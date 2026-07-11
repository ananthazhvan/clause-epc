"""Minimal schema validation for rules and claims. Zero external dependencies.

Each field spec: name -> (allowed_python_types, required, allowed_string_values_or_None)
NEVER loosen these to make a failing run pass - fix extraction instead.
"""

RULE_FIELDS = {
    "parameter": (str, True, None),
    "operator": (str, True, {">=", "<=", "==", "!=", "in", "exists", "absent", "range"}),
    "value": ((int, float, str, list, type(None)), True, None),
    "unit": ((str, type(None)), True, None),
    "condition": ((str, type(None)), True, None),
    "quote": (str, True, None),
}

CLAIM_FIELDS = {
    "parameter": (str, True, None),
    "value": ((int, float, str, type(None)), True, None),
    "unit": ((str, type(None)), True, None),
    "condition": ((str, type(None)), True, None),
    "location": (str, True, {"table", "footnote", "compliance_matrix", "transmittal", "prose", "curve_caption"}),
    "quote": (str, True, None),
    "confidence": ((int, float), True, None),
}


def validate_items(items, fields, label):
    """Returns a list of error strings; empty list means valid."""
    errors = []
    if not isinstance(items, list):
        return [f"{label}: expected a JSON list, got {type(items).__name__}"]
    for i, obj in enumerate(items):
        if not isinstance(obj, dict):
            errors.append(f"{label}[{i}]: each item must be an object")
            continue
        for name, (typ, required, allowed) in fields.items():
            if name not in obj:
                if required:
                    errors.append(f"{label}[{i}]: missing field '{name}'")
                continue
            v = obj[name]
            if not isinstance(v, typ):
                errors.append(f"{label}[{i}].{name}: wrong type {type(v).__name__}")
                continue
            if allowed and isinstance(v, str) and v not in allowed:
                errors.append(f"{label}[{i}].{name}: '{v}' not one of {sorted(allowed)}")
        extra = set(obj) - set(fields)
        if extra:
            errors.append(f"{label}[{i}]: unexpected fields {sorted(extra)}")
    return errors
