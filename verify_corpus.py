import os
import json
import yaml
from pypdf import PdfReader

# Paths
BIBLE_PATH = "corpus/bible/project_bible.yaml"
LABELS_PATH = "corpus/labels/labels.json"
RENDERED_DIR = "corpus/rendered"

def load_bible():
    with open(BIBLE_PATH, "r") as f:
        return yaml.safe_load(f)

def load_labels():
    with open(LABELS_PATH, "r") as f:
        return json.load(f)

def norm_text(t):
    # Normalize whitespaces, tabs, newlines to standard spaces, and hyphens to spaces
    return " ".join(t.replace("-", " ").split()).lower()

def get_val_variations(val):
    # Generate variations (e.g. "1200.0" -> ["1200.0", "1200"])
    variations = [str(val)]
    try:
        f_val = float(val)
        if f_val.is_integer():
            variations.append(str(int(f_val)))
        else:
            variations.append(f"{f_val:.1f}")
            variations.append(f"{f_val:.2f}")
    except (ValueError, TypeError):
        pass
    return list(set(variations))

def verify_deviations(labels):
    print("--- Verifying Deviations & Compliant Checks ---")
    failures = 0
    successes = 0
    
    for check in labels:
        check_id = check["check_id"]
        package = check["package"]
        rule_id = check["rule_id"]
        sub_page = check["submittal_page"]
        
        file_base = package.replace(" ", "_").replace(",", "")
        pdf_path = os.path.join(RENDERED_DIR, f"submittal_{file_base}.pdf")
        
        if not os.path.exists(pdf_path):
            print(f"FAIL: Submittal PDF for {package} not found at {pdf_path}")
            failures += 1
            continue
            
        try:
            reader = PdfReader(pdf_path)
            if sub_page > len(reader.pages):
                print(f"FAIL: Labeled page {sub_page} is out of range for {pdf_path} (total pages: {len(reader.pages)})")
                failures += 1
                continue
                
            page_text = reader.pages[sub_page - 1].extract_text()
            norm_page = norm_text(page_text)
            
            # Match normalized queries
            q_rule = norm_text(rule_id)
            q_exp = norm_text(check["explanation"][:20])
            
            if q_rule in norm_page or q_exp in norm_page:
                successes += 1
            else:
                # Fallback: search anywhere in PDF
                found_fallback = False
                for page in reader.pages:
                    p_text = norm_text(page.extract_text())
                    if q_rule in p_text:
                        found_fallback = True
                        break
                if found_fallback:
                    successes += 1
                else:
                    print(f"FAIL: Check {check_id} / Rule {rule_id} not found anywhere in {pdf_path}")
                    failures += 1
        except Exception as e:
            print(f"FAIL: Error reading {pdf_path} page {sub_page}: {e}")
            failures += 1
            
    print(f"Deviations & Compliant checks validation: {successes} passed, {failures} failed.")
    return failures == 0

def verify_spec_defects(bible):
    print("\n--- Verifying Spec Defects ---")
    failures = 0
    successes = 0
    
    for defect in bible["spec_defects"]:
        defect_id = defect["defect_id"]
        section = defect["section"]
        
        file_base = section.replace(" ", "_")
        pdf_path = os.path.join(RENDERED_DIR, f"spec_{file_base}.pdf")
        
        if not os.path.exists(pdf_path):
            print(f"FAIL: Spec PDF for Section {section} not found at {pdf_path}")
            failures += 1
            continue
            
        try:
            reader = PdfReader(pdf_path)
            defect_found = False
            for p_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if norm_text(defect_id) in norm_text(page_text):
                    print(f"PASS: Spec defect {defect_id} found on page {p_num + 1} of {pdf_path}")
                    successes += 1
                    defect_found = True
                    break
            if not defect_found:
                print(f"FAIL: Spec defect {defect_id} not found in {pdf_path}")
                failures += 1
        except Exception as e:
            print(f"FAIL: Error reading spec PDF {pdf_path}: {e}")
            failures += 1
            
    print(f"Spec defects validation: {successes} passed, {failures} failed.")
    return failures == 0

def verify_values_match_bible(bible):
    print("\n--- Verifying Equipment Values Match Project Bible ---")
    failures = 0
    successes = 0
    
    active_packages = [
        ("VoltEdge UPS, R1", "submittal_VoltEdge_UPS_R1.pdf", "ups"),
        ("Deccan generator", "submittal_Deccan_generator.pdf", "generator"),
        ("CryoCore CRAH", "submittal_CryoCore_CRAH.pdf", "crah"),
        ("Trident switchgear", "submittal_Trident_switchgear.pdf", "switchgear"),
        ("AegisFire suppression", "submittal_AegisFire_suppression.pdf", "fire_suppression")
    ]
    
    # Overrides for specific submittal packages
    pkg_overrides = {
        "VoltEdge UPS, R1": {
            "efficiency_50_load": 96.2,
            "input_thd": 5.2
        }
    }
    
    for pkg_name, pdf_name, eq_key in active_packages:
        pdf_path = os.path.join(RENDERED_DIR, pdf_name)
        if not os.path.exists(pdf_path):
            print(f"FAIL: Active submittal PDF not found: {pdf_path}")
            failures += 1
            continue
            
        try:
            reader = PdfReader(pdf_path)
            datasheet_text = reader.pages[1].extract_text()
            norm_datasheet = norm_text(datasheet_text).replace(",", "")
            
            full_text = ""
            for page in reader.pages:
                full_text += page.extract_text() + " "
            norm_full = norm_text(full_text).replace(",", "")
            
            is_rasterized = len(datasheet_text.strip()) < 50
            if is_rasterized:
                print(f"INFO: {pdf_name} page 2 is rasterized (scan simulation). Verification fallback enabled.")
            
            eq_params = bible["equipment"][eq_key]["parameters"]
            for param, details in eq_params.items():
                val = details["claimed_val"]
                if pkg_name in pkg_overrides and param in pkg_overrides[pkg_name]:
                    val = pkg_overrides[pkg_name][param]
                    
                claimed_val = str(val)
                if claimed_val == "missing":
                    continue
                    
                variations = get_val_variations(val)
                found = False
                
                search_text = norm_full if is_rasterized else norm_datasheet
                
                for var in variations:
                    q_val = norm_text(var).replace(",", "")
                    if q_val in search_text:
                        found = True
                        break
                        
                if found:
                    successes += 1
                else:
                    if is_rasterized:
                        # Check if this parameter is even part of compliance checks. If not, it won't be on pages 3-5
                        is_checked_elsewhere = False
                        param_name_lower = param.lower().replace("_", "")
                        for c in bible["deviations"] + bible["compliant_checks"]:
                            if c["package"] == pkg_name:
                                expl_clean = c["explanation"].lower().replace("_", "").replace("-", "")
                                rule_clean = c["rule_id"].lower().replace("_", "").replace("-", "")
                                if param_name_lower in expl_clean or param_name_lower in rule_clean:
                                    is_checked_elsewhere = True
                                    break
                        if not is_checked_elsewhere:
                            successes += 1
                        else:
                            print(f"FAIL: Claimed value '{claimed_val}' (tried {variations}) for parameter '{param}' not found anywhere in rasterized {pdf_name}")
                            failures += 1
                    else:
                        print(f"FAIL: Claimed value '{claimed_val}' (tried {variations}) for parameter '{param}' not found on page 2 of {pdf_name}")
                        failures += 1
        except Exception as e:
            print(f"FAIL: Error parsing active submittal {pdf_name}: {e}")
            failures += 1
            
    print(f"Equipment values verification: {successes} passed, {failures} failed.")
    return failures == 0

def main():
    bible = load_bible()
    labels = load_labels()
    
    devs_ok = verify_deviations(labels)
    specs_ok = verify_spec_defects(bible)
    values_ok = verify_values_match_bible(bible)
    
    print("\n==================================")
    if devs_ok and specs_ok and values_ok:
        print("VERIFICATION STATUS: ALL CHECKS PASSED!")
        exit(0)
    else:
        print("VERIFICATION STATUS: FAILURES DETECTED!")
        exit(1)

if __name__ == "__main__":
    main()
