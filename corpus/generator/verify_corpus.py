import os
import re
import json
import sys
import pypdf
import yaml
import copy

RENDERED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "rendered"))
LABELS_PATH = os.path.join(RENDERED_DIR, "labels.json")
BIBLE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bible", "project_bible.yaml"))
CURVES_PATH = os.path.join(RENDERED_DIR, "curves_data.json")

check_to_param = {
    # Deviations
    "DEV-UPS-R0-EFF50": "efficiency_50_load",
    "DEV-UPS-R0-RED": "parallel_redundancy",
    "DEV-UPS-R0-CERT": "certification",
    "DEV-UPS-R0-REV": "spec_revision",
    "DEV-UPS-R0-MISS-PARAM": "bypass_transfer_time_ms",
    "DEV-UPS-R0-OVERLOAD": "overload_capacity",
    "DEV-UPS-R0-AIRFLOW-PATH": "cooling_airflow_path",
    "DEV-UPS-R0-PAINT": "enclosure_paint_finish",
    "DEV-GEN-TEMP": "reference_ambient_temp_c",
    "DEV-GEN-SHORTFALL": "derated_standby_capacity",
    "DEV-GEN-OBS-CERT": "generator_controller",
    "DEV-GEN-AMB-VENT": "room_ventilation",
    "DEV-GEN-DAYTANK": "day_tank_capacity_l",
    "DEV-GEN-MISS-PARAM": "fuel_consumption_50_l_h",
    "DEV-GEN-STARTER": "electric_starter_motors",
    "DEV-GEN-SOUND": "sound_pressure_level_dba",
    "DEV-CRAH-AIRFLOW": "airflow_m3_h",
    "DEV-CRAH-AMB-CHW": "cop",
    "DEV-CRAH-UNIT-HP": "fan_motor_power",
    "DEV-CRAH-REFRIGERANT": "refrigerant",
    "DEV-CRAH-MISS-PARAM": "valve_flow_coefficient",
    "DEV-CRAH-HUMIDIFIER": "humidifier_type",
    "DEV-CRAH-VALVE-TYPE": "control_valve_type",
    "DEV-CRAH-WIDTH": "cabinet_width_mm",
    "DEV-FIRE-CERT-MISS": "factory_test_certificate",
    "DEV-FIRE-STD-OBS": "standard_edition_compliance",
    "DEV-FIRE-DISCH-FOOT": "discharge_time_s",
    "DEV-FIRE-HOLDTIME": "hold_time_min",
    "DEV-FIRE-MISS-PARAM": "noael_safety_margin_calculation",
    "DEV-FIRE-PRESSURE": "cylinder_pressure_rating",
    "DEV-FIRE-QUANTITY": "clean_agent_quantity_kg",
    "DEV-FIRE-STANDARDS": "cylinder_certification_standard",
    "DEV-UPS-R1-THD": "input_thd",
    "DEV-UPS-R1-ADD3-EFF100": "efficiency_100_load",
    "DEV-UPS-R1-ADD3-EFF75": "efficiency_75_load",
    "DEV-UPS-R1-ADD3-EFF50": "efficiency_50_load",
    "DEV-UPS-R1-MISS-PARAM": "bypass_transfer_time_ms",
    "DEV-UPS-R1-OVERLOAD": "overload_capacity",
    "DEV-UPS-R1-AIRFLOW-PATH": "cooling_airflow_path",
    "DEV-UPS-R1-PAINT": "enclosure_paint_finish",
    "DEV-BAT-UNIT-SHORTFALL": "nominal_capacity",
    "DEV-BAT-COND-PF": "runtime_load_pf",
    "DEV-BAT-DCBUS": "nominal_dc_bus_voltage",
    "DEV-BAT-MISS-PARAM": "battery_shelf_life",
    "DEV-BAT-CABINET-WEIGHT": "fully_loaded_weight",
    "DEV-BAT-OPERATING-TEMP": "operating_temperature_range",
    "DEV-BAT-CABLE-ENTRY": "cable_entry_configuration",
    "DEV-BAT-LVD-VALVE": "lvd_contactor_rating",
    
    # Compliant Checks
    "COMP-SWG-VOLT": "voltage_kv",
    "COMP-SWG-AMP": "busbar_current_a",
    "COMP-SWG-KA": "short_circuit_withstand_ka",
    "COMP-SWG-TIME": "short_circuit_duration_s",
    "COMP-SWG-IP": "ip_rating",
    "COMP-SWG-IAC": "internal_arc_class",
    "COMP-SWG-CERT": "certification",
    "COMP-SWG-MAKING": "making_capacity_ka_peak",
    "COMP-SWG-BIL": "lightning_impulse_withstand_voltage",
    "COMP-SWG-BUS-MAT": "busbar_material",
    "COMP-SWG-EARTH": "earthing_busbar_material",
    "COMP-SWG-CT-ACC": "ct_accuracy_class",
    "COMP-SWG-VT-ACC": "vt_accuracy_class",
    "COMP-SWG-OPER-TEMP": "operating_temperature_range",
    "COMP-SWG-LSC": "loss_of_service_continuity",
    "COMP-UPS-R0-CAP": "capacity_kw",
    "COMP-UPS-R0-PF": "power_factor",
    "COMP-UPS-R0-THD": "input_thd",
    "COMP-UPS-R0-EFF100": "efficiency_100_load",
    "COMP-UPS-R0-EFF75": "efficiency_75_load",
    "COMP-GEN-PF": "power_factor",
    "COMP-GEN-VOLT": "voltage_kv",
    "COMP-GEN-SPEED": "speed_rpm",
    "COMP-GEN-LOAD": "block_load_acceptance",
    "COMP-GEN-GOVERNOR": "governor_type",
    "COMP-CRAH-CAP": "sensible_cooling_kw",
    "COMP-CRAH-CHW-IN": "entering_water_temp_c",
    "COMP-CRAH-CHW-OUT": "leaving_water_temp_c",
    "COMP-CRAH-FAN-EFF": "fan_power_density_w_m3_h",
    "COMP-CRAH-HUMIDITY-RANGE": "operating_humidity_range",
    "COMP-FIRE-AGENT": "agent_type",
    "COMP-FIRE-CONC": "design_concentration_pct",
    "COMP-FIRE-NOAEL": "noael_limit_pct",
    "COMP-UPS-R1-CAP": "capacity_kw",
    "COMP-UPS-R1-PF": "power_factor",
    "COMP-UPS-R1-CERT": "certification",
    "COMP-UPS-R1-REV": "spec_revision",
    "DEV-BAT-UNIT-KWH": "nominal_capacity"
}

package_map = {
    "VoltEdge UPS, R0": {"eq": "ups"},
    "VoltEdge UPS, R1": {"eq": "ups"},
    "VoltEdge battery cabinet": {"eq": "battery"},
    "Deccan generator": {"eq": "generator"},
    "CryoCore CRAH": {"eq": "crah"},
    "Trident switchgear": {"eq": "switchgear"},
    "AegisFire suppression": {"eq": "fire_suppression"}
}

def extract_text_pypdf(pdf_path, page_num):
    with open(pdf_path, 'rb') as f:
        reader = pypdf.PdfReader(f)
        if 1 <= page_num <= len(reader.pages):
            return reader.pages[page_num - 1].extract_text()
    return ""

def extract_all_text(pdf_path):
    text = ""
    with open(pdf_path, 'rb') as f:
        reader = pypdf.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    return text

def normalize_text(text):
    text = re.sub(r'\s+', ' ', text)
    text = text.replace(',', '')
    text = text.replace('\u00b0', '°')
    return text.lower()

def value_token_in_text(val, text):
    norm_val = normalize_text(str(val))
    norm_text = normalize_text(text)
    if norm_val in norm_text:
        return True
    if isinstance(val, float) and val.is_integer():
        if str(int(val)) in norm_text:
            return True
    if isinstance(val, str):
        tokens = val.lower().replace(",", "").split()
        if all(t in norm_text for t in tokens):
            return True
    return False

def main():
    if not os.path.exists(LABELS_PATH):
        print("Error: labels.json not found")
        sys.exit(1)
        
    with open(LABELS_PATH, "r") as f:
        labels = json.load(f)
        
    with open(BIBLE_PATH, "r") as f:
        bible = yaml.safe_load(f)
        
    curves_data = {}
    if os.path.exists(CURVES_PATH):
        with open(CURVES_PATH) as f:
            curves_data = json.load(f)
            
    # Pre-build parameter overrides for all packages
    pkg_params = {}
    for pkg_name, meta in package_map.items():
        eq_key = meta["eq"]
        if not eq_key:
            continue
        params = copy.deepcopy(bible["equipment"][eq_key]["parameters"])
        overrides = bible["submittal_packages"].get(pkg_name, {}).get("parameter_overrides", {})
        for pk, o_data in overrides.items():
            if pk in params:
                params[pk].update(o_data)
            else:
                params[pk] = o_data
        pkg_params[pkg_name] = params
        
    all_passed = True
    print(f"Verifying {len(labels)} labels...")
    
    for label in labels:
        cid = label["check_id"]
        # Verify Spec PDF
        spec_pdf = os.path.join(RENDERED_DIR, label["spec_pdf"])
        spec_page = label["spec_page"]
        if spec_page:
            text = extract_text_pypdf(spec_pdf, spec_page)
            norm_text = normalize_text(text)
            
            clause_str = label["spec_clause"]
            
            section_id = label["spec_pdf"].replace(".pdf", "").replace("_", " ")
            matches = re.findall(r'(\d{2} \d{2} \d{2}\s+Part\s+[\d\.A-Za-z]+)', clause_str)
            target_match = None
            for m in matches:
                if m.startswith(section_id):
                    target_match = m
                    break
                    
            if target_match:
                after_part = target_match.split("Part")[-1]
                search_clause = normalize_text(after_part.strip())
            else:
                after_part = clause_str.split("Part")[-1]
                search_clause = normalize_text(after_part.split("vs")[0].strip())
                
            if search_clause not in norm_text:
                print(f"FAIL: {cid} - Clause {search_clause} not found on {label['spec_pdf']} page {spec_page}")
                all_passed = False
                
        # Verify Submittal PDF
        sub_pdf = label["submittal_pdf"]
        sub_page = label["submittal_page"]
        where_expressed = label.get("where_expressed", "main table")
        pkg_name = label.get("package")
        
        # Look up backing parameter claimed value
        claimed_val = None
        param_display_name = None
        param_key = check_to_param.get(cid)
        if param_key and pkg_name in pkg_params and param_key in pkg_params[pkg_name]:
            claimed_val = pkg_params[pkg_name][param_key]["claimed_val"]
            param_display_name = pkg_params[pkg_name][param_key]["display_name"]
            
        if sub_pdf:
            sub_pdf_path = os.path.join(RENDERED_DIR, sub_pdf)
            
            if where_expressed == "curve":
                # Verify against curves_data.json
                if pkg_name not in curves_data:
                    print(f"FAIL: {cid} - Package {pkg_name} not found in curves_data.json")
                    all_passed = False
                else:
                    x_arr = curves_data[pkg_name]["x"]
                    y_arr = curves_data[pkg_name]["y"]
                    if cid == "DEV-GEN-SHORTFALL":
                        point_found = False
                        for x, y in zip(x_arr, y_arr):
                            if x == 45 and y == 2450:
                                point_found = True
                                break
                        if not point_found:
                            print(f"FAIL: {cid} - Curve point (45, 2450) not found in curves_data.json for Deccan generator")
                            all_passed = False
                    elif cid == "DEV-UPS-R0-EFF50":
                        point_found = False
                        for x, y in zip(x_arr, y_arr):
                            if x == 50 and y == 95.1:
                                point_found = True
                                break
                        if not point_found:
                            print(f"FAIL: {cid} - Curve point (50, 95.1) not found in curves_data.json for R0 UPS")
                            all_passed = False
                    elif cid == "DEV-UPS-R1-ADD3-EFF50":
                        point_found = False
                        for x, y in zip(x_arr, y_arr):
                            if x == 50 and y == 96.2:
                                point_found = True
                                break
                        if not point_found:
                            print(f"FAIL: {cid} - Curve point (50, 96.2) not found in curves_data.json for R1 UPS")
                            all_passed = False
            elif where_expressed == "missing":
                page2_text = extract_text_pypdf(sub_pdf_path, 2)
                if param_display_name and normalize_text(param_display_name) in normalize_text(page2_text):
                    print(f"FAIL: {cid} - Parameter display name '{param_display_name}' found on {sub_pdf} page 2 (should be missing)")
                    all_passed = False
            else:
                # Normal text check on labeled page for clause ID
                text = extract_text_pypdf(sub_pdf_path, sub_page)
                norm_text = normalize_text(text)
                
                # Check clause ID
                clause_str = label["spec_clause"]
                match = re.search(r'(\d{2} \d{2} \d{2}\s+Part\s+[\d\.A-Za-z]+)', clause_str)
                if match:
                    search_clause = normalize_text(match.group(1))
                else:
                    search_clause = normalize_text(clause_str.split("vs")[0].strip())
                    
                if search_clause not in norm_text:
                    print(f"FAIL: {cid} - Clause {search_clause} not found on {sub_pdf} page {sub_page}")
                    all_passed = False
                    
                # Check claimed value presence on the correct page
                chk_val = claimed_val
                if cid == "DEV-BAT-UNIT-SHORTFALL":
                    chk_val = "1145.8 Ah"
                elif cid == "DEV-BAT-UNIT-KWH":
                    chk_val = "1200 Ah"
                elif cid == "DEV-FIRE-HOLDTIME":
                    chk_val = "9 minutes"
                elif cid in ["DEV-UPS-R0-CERT", "COMP-UPS-R1-CERT"]:
                    chk_val = "IEC 62040-3"
                    
                val_page = sub_page
                if where_expressed in ["main table", "footnote"]:
                    val_page = 2
                elif where_expressed == "transmittal":
                    val_page = 1
                
                val_text = extract_text_pypdf(sub_pdf_path, val_page)
                
                if chk_val is not None and chk_val != "missing":
                    if not value_token_in_text(chk_val, val_text):
                        print(f"FAIL: {cid} - Claimed value '{chk_val}' not found on {sub_pdf} page {val_page}")
                        all_passed = False
                        
    # Check forbidden words in base specs
    forbidden_words = ["check_id", "defect_id", "deviation type", "ground truth", "addendum"]
    base_specs = ["26_05_00.pdf", "26_33_53.pdf", "26_32_13.pdf", "26_13_26.pdf", "23_81_23.pdf", "21_22_00.pdf"]
    
    for spec in base_specs:
        spec_path = os.path.join(RENDERED_DIR, spec)
        if not os.path.exists(spec_path):
            continue
            
        full_text = normalize_text(extract_all_text(spec_path))
        
        if "def-" in full_text or "dev-" in full_text or "comp-" in full_text:
            print(f"FAIL: Forbidden ID pattern found in {spec}")
            all_passed = False
            
        for fw in forbidden_words:
            if fw in full_text:
                print(f"FAIL: Forbidden word '{fw}' found in {spec}")
                all_passed = False
                
        if re.search(r'\btier\s*(?:t1|t2|t3|:)', full_text):
            print(f"FAIL: Forbidden word 'tier' (label context) found in {spec}")
            all_passed = False
            
    if all_passed:
        print("✓ All labels verified successfully.")
        print("✓ No forbidden words in base specs.")
        sys.exit(0)
    else:
        print("Verification failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
