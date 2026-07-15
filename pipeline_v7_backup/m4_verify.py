"""M4 - deterministic verdict engine.

Joins compiled rulebooks (M2) against submittal claims (M3) and produces a
deviation register. ZERO LLM calls: every verdict is a pure function of the
extracted artifacts, fully reproducible, and every verdict carries the
verbatim quotes and page numbers from BOTH sides (spec + submittal).

Verdicts
  COMPLY            evidence exists and satisfies the rule
  DEVIATION         evidence exists and violates the rule
  MISSING_EVIDENCE  no claim addresses the rule's parameter
  NEEDS_REVIEW      evidence exists but cannot be compared mechanically
                    (non-numeric value, unit mismatch, unparseable rule)

Flags
  false_comply            vendor stamped Comply on the clause but the evidence violates it
  unsubstantiated_comply  vendor stamped Comply but provided no measurable evidence
  conflict                multiple evidence claims disagree on the same parameter
  condition_unverified    rule has a measurement condition no claim clearly states

Design rules:
- Never guess unit conversions: mismatched units go to NEEDS_REVIEW.
- When multiple claims cover one parameter, the claim whose stated condition
  best matches the rule's condition GOVERNS (this is what catches the
  footnote trap: a footnote value measured under the spec's condition beats a
  headline table value measured under a friendlier one).
- Addendum precedence is NOT applied here yet; verdicts are against the base
  spec revision (M5 layers document precedence on top).
"""
import argparse
import glob
import json
import os
import re

STOP = {"the", "a", "an", "of", "in", "at", "with", "and", "or", "shall", "be",
        "is", "are", "when", "under", "to", "for", "per", "on", "all", "as", "by"}

UNIT_ALIASES = {
    "percent": "%", "pct": "%",
    "deg c": "degc", "\u00b0c": "degc", "celsius": "degc", "c": "degc",
    "v dc": "vdc", "v ac": "vac",
    "db(a)": "dba",
    "m\u00b3/h": "m3/h", "cmh": "m3/h",
    "litres": "l", "liters": "l", "litre": "l", "liter": "l",
    "minutes": "min", "minute": "min",
    "seconds": "s", "second": "s", "sec": "s",
    "hours": "h", "hour": "h", "hr": "h",
}


def norm_unit(u):
    if u is None or str(u).strip() == "":
        return None
    u = re.sub(r"\s+", " ", str(u).strip().lower())
    return UNIT_ALIASES.get(u, u)


def parse_number(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.replace(",", "").strip()
        if re.fullmatch(r"[-+]?\d+(?:\.\d+)?", s):
            return float(s)
    return None


def norm_str(v):
    return re.sub(r"\s+", " ", str(v).strip().lower())


def tokens(s):
    return {t for t in re.findall(r"[a-z0-9]+", (s or "").lower()) if t not in STOP}


def cond_score(rule_cond, claim_cond):
    """Overlap 0..1 between the rule's measurement condition and a claim's."""
    rt = tokens(rule_cond)
    if not rt:
        return 1.0  # unconditional rule: every claim qualifies equally
    ct = tokens(claim_cond)
    if not ct:
        return 0.0  # conditional rule, claim states no condition
    return len(rt & ct) / len(rt)


def parse_range(value):
    if isinstance(value, (list, tuple)) and len(value) == 2:
        lo, hi = parse_number(value[0]), parse_number(value[1])
        if lo is not None and hi is not None:
            return lo, hi
    if isinstance(value, str):
        m = re.fullmatch(r"\s*([-+]?\d+(?:\.\d+)?)\s*(?:-|to)\s*([-+]?\d+(?:\.\d+)?)\s*", value)
        if m:
            return float(m.group(1)), float(m.group(2))
    return None


def related_stamp(stamp, rule):
    part_id = rule["source_clause"].split(" Part ")[-1]
    q = stamp.get("quote") or ""
    return (rule["source_clause"] in q or part_id in q
            or stamp.get("parameter") == rule["parameter"])


def compare(op, val, rule_value):
    """Returns True (satisfies), False (violates), or None (not comparable)."""
    req = parse_number(rule_value)
    if op == ">=":
        return None if req is None or val is None else val >= req
    if op == "<=":
        return None if req is None or val is None else val <= req
    if op == "range":
        rng = parse_range(rule_value)
        return None if rng is None or val is None else rng[0] <= val <= rng[1]
    return None


def str_satisfies(a, b):
    """True iff one normalized string equals or contains the other as a whole
    word ('0.8' satisfies '0.8 lagging'; 'copper' satisfies 'high conductivity
    copper'). Contradictory content ('R-407C' vs 'R-410A') does NOT satisfy.
    Containment is normalization of wording, never fuzzy similarity."""
    na, nb = norm_str(a), norm_str(b)
    if na == nb:
        return True
    shorter, longer = sorted([na, nb], key=len)
    if not shorter:
        return False
    return re.search(r"(?<![a-z0-9])" + re.escape(shorter) + r"(?![a-z0-9])", longer) is not None


def compare_equality(op, claim_value, rule_value):
    cn, rn = parse_number(claim_value), parse_number(rule_value)
    if cn is not None and rn is not None:
        same = abs(cn - rn) < 1e-9
    else:
        same = str_satisfies(claim_value, rule_value)
    return same if op == "==" else (not same)


def evaluate_rule(rule, evidence, stamps, in_scope=True):
    op = rule["operator"]
    cands = [c for c in evidence if c["parameter"] == rule["parameter"]]
    rel_stamps = [s for s in stamps if related_stamp(s, rule)]
    stamp_comply = any(norm_str(s.get("value", "")).startswith("comply") for s in rel_stamps)

    result = {
        "rule_id": rule["rule_id"],
        "parameter": rule["parameter"],
        "requirement": rule,
        "claims": cands,
        "stamps": rel_stamps,
        "flags": [],
        "governing_claim": None,
        "reason": "",
    }

    def finish(verdict, reason):
        result["verdict"] = verdict
        result["reason"] = reason
        if verdict == "DEVIATION" and stamp_comply:
            result["flags"].append("false_comply")
        if verdict == "MISSING_EVIDENCE" and stamp_comply:
            result["flags"].append("unsubstantiated_comply")
        return result

    # existence-style rules first
    if op == "absent":
        if cands:
            result["governing_claim"] = cands[0]
            return finish("DEVIATION", "parameter must be absent but the submittal claims it")
        return finish("COMPLY", "parameter correctly absent")
    if op == "exists":
        if cands:
            result["governing_claim"] = cands[0]
            return finish("COMPLY", "required item is present in the submittal")
        if not rel_stamps and not in_scope:
            return finish("NOT_ADDRESSED", "clause family not addressed by this package")
        return finish("MISSING_EVIDENCE", "required item not found in any claim")

    if not cands:
        if not rel_stamps and not in_scope:
            # Clause family entirely outside what this package addresses
            # (a battery datasheet does not answer UPS efficiency clauses).
            return finish("NOT_ADDRESSED", "clause family not addressed by this package")
        return finish("MISSING_EVIDENCE", "package addresses this clause family but provides no evidence for the parameter")

    # split candidates into mechanically comparable vs not
    r_unit = norm_unit(rule.get("unit"))
    comparable, unit_mismatch, non_numeric = [], [], []
    for c in cands:
        if op in ("==", "!=", "in"):
            comparable.append(c)
            continue
        val = parse_number(c.get("value"))
        if val is None:
            non_numeric.append(c)
            continue
        c_unit = norm_unit(c.get("unit"))
        if r_unit and c_unit and r_unit != c_unit:
            unit_mismatch.append(c)
            continue
        comparable.append(c)
    if not comparable:
        why = []
        if unit_mismatch:
            why.append(f"unit mismatch ({rule.get('unit')} vs {unit_mismatch[0].get('unit')})")
        if non_numeric:
            why.append(f"non-numeric evidence ({non_numeric[0].get('value')!r})")
        return finish("NEEDS_REVIEW", "; ".join(why) or "no comparable evidence")

    # condition-matched claims govern
    scored = [(cond_score(rule.get("condition"), c.get("condition")), c) for c in comparable]
    best = max(s for s, _ in scored)
    governing = [c for s, c in scored if s == best]
    if rule.get("condition") and best < 0.5:
        result["flags"].append("condition_unverified")

    # conflicting evidence?
    vals = {parse_number(c.get("value")) for c in comparable}
    vals.discard(None)
    if len(vals) > 1:
        result["flags"].append("conflict")

    verdicts = []
    for c in governing:
        if op in ("==", "!="):
            ok = compare_equality(op, c.get("value"), rule.get("value"))
        elif op == "in":
            allowed = rule.get("value")
            allowed = allowed if isinstance(allowed, list) else [allowed]
            ok = any(str_satisfies(c.get("value"), a) for a in allowed)
        else:
            ok = compare(op, parse_number(c.get("value")), rule.get("value"))
        verdicts.append((ok, c))

    if any(ok is None for ok, _ in verdicts):
        return finish("NEEDS_REVIEW", f"rule value {rule.get('value')!r} not mechanically comparable")
    violating = [c for ok, c in verdicts if ok is False]
    passing = [c for ok, c in verdicts if ok is True]

    if violating and passing:
        # governing evidence contradicts itself at equal condition match:
        # a machine must not pick a side here.
        result["governing_claim"] = violating[0]
        return finish("NEEDS_REVIEW",
                      f"conflicting governing evidence: {passing[0].get('value')} vs {violating[0].get('value')}"
                      f" {rule.get('unit') or ''} - human must determine which figure governs")

    if violating:
        c = violating[0]
        result["governing_claim"] = c
        if op in ("==", "in") and parse_number(c.get("value")) is None:
            ct, rt = tokens(str(c.get("value"))), tokens(str(rule.get("value")))
            if ct and ct < rt:
                # Claim wording is a proper subset of the requirement
                # ('High conductivity copper' vs 'high conductivity
                # electrolytic copper'): it omits a qualifier rather than
                # contradicting the spec. A machine cannot prove a violation.
                return finish("NEEDS_REVIEW",
                              f"stated {c.get('value')!r} omits required qualifier(s) {sorted(rt - ct)} - confirm with vendor")
        return finish(
            "DEVIATION",
            f"required {rule['parameter']} {op} {rule['value']} {rule.get('unit') or ''};"
            f" governing evidence says {c.get('value')} {c.get('unit') or ''}"
            f" ({c.get('location')}, p{c.get('page')})",
        )

    result["governing_claim"] = verdicts[0][1]
    if "condition_unverified" in result["flags"]:
        # Value passes, but it was not measured under the rule's required
        # condition (e.g. rated kVA at 40degC offered against a 45degC clause).
        # Passing under a friendlier condition proves nothing.
        return finish("NEEDS_REVIEW",
                      "value satisfies the limit but no evidence is measured under the rule's condition"
                      f" ({rule.get('condition')!r})")
    return finish("COMPLY", "governing evidence satisfies the rule")


def verify_package(claims_path, out_dir):
    doc = json.load(open(claims_path))
    pkg, section = doc["package"], doc["section"]
    stem = section.replace(" ", "_")
    rb_path = os.path.join(out_dir, f"rulebook_{stem}.json")
    if not os.path.exists(rb_path):
        print(f"SKIP {pkg}: no rulebook for section {section}")
        return None
    rules = json.load(open(rb_path))["rules"]
    rule_params = {r["parameter"] for r in rules}
    prefixes = {p.split(".", 1)[0] for p in rule_params if "." in p}

    def resolve_param(p):
        """Exact-suffix prefix normalization ONLY (never fuzzy): the extractor
        sometimes drops the ontology prefix (busbar_material vs
        swgr.busbar_material). If exactly one prefixed rule parameter has this
        exact suffix, use it. unmapped.* stays unmapped by design."""
        if p in rule_params or "." in p:
            return p
        hits = [f"{pre}.{p}" for pre in prefixes if f"{pre}.{p}" in rule_params]
        return hits[0] if len(hits) == 1 else p

    claims = []
    seen = set()
    n_norm = 0
    for c in doc["claims"]:
        c = dict(c)
        rp = resolve_param(c["parameter"])
        if rp != c["parameter"]:
            c["parameter_as_extracted"] = c["parameter"]
            c["parameter"] = rp
            n_norm += 1
        key = (c["parameter"], norm_str(c.get("value")), c.get("page"), c.get("location"), norm_str(c.get("condition") or ""))
        if key in seen:
            continue
        seen.add(key)
        claims.append(c)
    if n_norm:
        print(f"  note: {pkg}: normalized {n_norm} claim parameter(s) to ontology prefix (exact suffix match)")
    evidence = [c for c in claims if c.get("location") != "compliance_matrix"]
    stamps = [c for c in claims if c.get("location") == "compliance_matrix"]

    # Which clause families (e.g. "2.3") does this package actually address?
    # A battery submittal does not answer UPS efficiency clauses; but inside a
    # family it does address, silence on a required parameter is a finding.
    def family(clause):
        part = clause.split(" Part ")[-1]
        bits = part.split(".")
        return ".".join(bits[:2]) if len(bits) >= 2 else bits[0]

    evid_params = {c["parameter"] for c in evidence}
    addressed = set()
    for r in rules:
        if r["parameter"] in evid_params or any(related_stamp(s, r) for s in stamps):
            addressed.add(family(r["source_clause"]))

    results = [evaluate_rule(r, evidence, stamps, family(r["source_clause"]) in addressed) for r in rules]
    summary = {}
    for r in results:
        summary[r["verdict"]] = summary.get(r["verdict"], 0) + 1
    out = {"package": pkg, "section": section, "summary": summary, "results": results}
    out_path = os.path.join(out_dir, f"verdicts_{pkg}.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=1)
    flagged = sum(1 for r in results if "false_comply" in r["flags"])
    print(f"{pkg} vs {section}: " + ", ".join(f"{k}={v}" for k, v in sorted(summary.items()))
          + (f"  [false_comply: {flagged}]" if flagged else ""))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out")
    ap.add_argument("--package", help="verify one package id, e.g. SUB-263353-01-R0")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()

    paths = ([os.path.join(a.out, f"claims_{a.package}.json")] if a.package
             else sorted(glob.glob(os.path.join(a.out, "claims_*.json"))))
    register = []
    for p in paths:
        out = verify_package(p, a.out)
        if out:
            for r in out["results"]:
                if r["verdict"] not in ("COMPLY", "NOT_ADDRESSED") or r["flags"]:
                    register.append({"package": out["package"], "section": out["section"], **r})
    reg_path = os.path.join(a.out, "deviation_register.json")
    with open(reg_path, "w") as f:
        json.dump(register, f, indent=1)
    print(f"\ndeviation register: {len(register)} open item(s) -> {reg_path}")


if __name__ == "__main__":
    main()
