import os
import re
import csv
import json
import yaml
import subprocess
import jinja2
import pypdf
import matplotlib.pyplot as plt
import io
import base64
import copy

BIBLE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bible", "project_bible.yaml"))
TEMPLATE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates"))
RENDERED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "rendered"))
LABELS_PATH = os.path.join(RENDERED_DIR, "labels.json")

env = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATE_DIR))
# Custom filter for rounding floats nicely
def fmt_val(val):
    if isinstance(val, float):
        if val.is_integer():
            return str(int(val))
        return str(val)
    return str(val)
env.filters['fmt'] = fmt_val

def render_pdf(html_str, out_pdf):
    tmp_html = out_pdf + ".html"
    with open(tmp_html, "w") as f:
        f.write(html_str)
    subprocess.run([
        "google-chrome", "--headless", "--disable-gpu", 
        "--no-margins", "--print-to-pdf-no-header",
        f"--print-to-pdf={out_pdf}", tmp_html
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.remove(tmp_html)

def extract_text_pypdf(pdf_path):
    pages_text = []
    with open(pdf_path, 'rb') as f:
        reader = pypdf.PdfReader(f)
        for page in reader.pages:
            pages_text.append(page.extract_text())
    return pages_text

def find_page_for_regex(pages_text, pattern):
    for i, page_text in enumerate(pages_text):
        page_norm = re.sub(r'\s+', ' ', page_text).strip()
        if re.search(pattern, page_norm):
            return i + 1
    return None

def export_csvs(bible):
    regs = bible.get("registers", {})
    for name, data in regs.items():
        if not data:
            continue
        csv_path = os.path.join(RENDERED_DIR, f"{name}.csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        print(f"Exported {csv_path}")

def get_clause_text(bible, clause_id):
    for sec_data in bible.get("clauses", {}).values():
        for part in sec_data.get("parts", []):
            for art in part.get("articles", []):
                for para in art.get("paragraphs", []):
                    if para["clause_id"] == clause_id:
                        return para["text"]
    return ""

def generate_specs(bible, labels_cache):
    specs = bible.get("clauses", {})
    for section_id, section_data in specs.items():
        title = section_data["title"]
        pages = []
        current_page = {"elements": []}
        count = 0
        
        for part in section_data.get("parts", []):
            current_page["elements"].append({"type": "part", "num": part["part"], "title": part["title"]})
            count += 2
            for article in part.get("articles", []):
                current_page["elements"].append({"type": "article", "num": article["number"], "title": article["title"]})
                count += 1
                for para in article.get("paragraphs", []):
                    current_page["elements"].append({"type": "paragraph", "clause_id": para["clause_id"], "text": para["text"]})
                    count += 1
                    if count >= 12:
                        pages.append(current_page)
                        current_page = {"elements": []}
                        count = 0
        if current_page["elements"]:
            pages.append(current_page)
            
        template = env.get_template("spec.html")
        html_str = template.render(section_id=section_id, section_title=title, pages=pages)
        pdf_name = f"{section_id.replace(' ', '_')}.pdf"
        out_pdf = os.path.join(RENDERED_DIR, pdf_name)
        render_pdf(html_str, out_pdf)
        
        # Parse for labels
        pages_text = extract_text_pypdf(out_pdf)
        # We save this for later cross-referencing
        labels_cache[pdf_name] = pages_text
        print(f"Generated {out_pdf}")

def create_plot(title, xlabel, ylabel, x_vals, y_vals):
    plt.figure(figsize=(6,4))
    plt.plot(x_vals, y_vals, marker='o')
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(True)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close()
    buf.seek(0)
    return "data:image/png;base64," + base64.b64encode(buf.read()).decode('utf-8')

def build_addendum(bible, labels_cache):
    changes = bible.get("addendum_3", {}).get("changes", [])
    pages = [{"blocks": [
        {"type": "heading", "text": "Addendum 3 Changes"},
        {"type": "paragraph", "text": "The following changes are issued to the contract documents."}
    ]}]
    for change in changes:
        pages[0]["blocks"].append({
            "type": "addendum_change",
            "reference": change["reference"],
            "action": change["action"],
            "clause": change.get("description", ""),
            "text": ""
        })
    template = env.get_template("generic.html")
    html_str = template.render(doc_type="Addendum", title="ADDENDUM 3", subtitle="Date: 15-06-2026", pages=pages)
    out_pdf = os.path.join(RENDERED_DIR, "addendum_3.pdf")
    render_pdf(html_str, out_pdf)
    labels_cache["addendum_3.pdf"] = extract_text_pypdf(out_pdf)
    print(f"Generated {out_pdf}")

def build_dbr(labels_cache):
    pages = [{"blocks": [
        {"type": "heading", "text": "Campus Overview"},
        {"type": "paragraph", "text": "Meridian Data Centre Campus Phase 1 supports 20MW IT load across 4 halls x 5MW."},
        {"type": "paragraph", "text": "Target PUE is 1.45."},
        {"type": "heading", "text": "Electrical Topology"},
        {"type": "paragraph", "text": "UPS systems shall be N+1 per group."},
        {"type": "heading", "text": "Consultant"},
        {"type": "paragraph", "text": "Designed by Apex Engineering."}
    ]}]
    template = env.get_template("generic.html")
    html_str = template.render(doc_type="Design Basis Report", title="Design Basis Report", pages=pages)
    out_pdf = os.path.join(RENDERED_DIR, "dbr.pdf")
    render_pdf(html_str, out_pdf)
    labels_cache["dbr.pdf"] = extract_text_pypdf(out_pdf)
    print(f"Generated {out_pdf}")

def build_fillers(labels_cache):
    fillers = [
        ("kickoff_minutes.pdf", "Kickoff Meeting Minutes", "Meeting held to discuss project kickoff."),
        ("ups_r0_review.pdf", "UPS R0 Review Minutes", "Review of VoltEdge UPS R0. Several deviations noted. Rejection likely."),
        ("method_statement.pdf", "Method Statement", "Installation methodology for electrical works."),
        ("change_order_1.pdf", "Change Order 1", "Approval for minor site variations.")
    ]
    template = env.get_template("generic.html")
    for fname, title, text in fillers:
        pages = [{"blocks": [{"type": "paragraph", "text": text}]}]
        html_str = template.render(doc_type="Project Document", title=title, pages=pages)
        out_pdf = os.path.join(RENDERED_DIR, fname)
        render_pdf(html_str, out_pdf)
        labels_cache[fname] = extract_text_pypdf(out_pdf)
        print(f"Generated {out_pdf}")

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

def fmt_claimed_val(val, unit):
    if isinstance(val, (int, float)):
        if isinstance(val, float) and val.is_integer():
            val = int(val)
        if unit and unit not in ["text", "dimensionless", "%", "degree"]:
            return f"{val} {unit}"
        elif unit == "%":
            return f"{val}%"
        elif unit == "degree":
            return f"{val}°"
        else:
            return str(val)
    return str(val)

def generate_submittals(bible, labels_cache):
    submittals = bible.get("submittal_packages", {})
    deviations = bible.get("deviations", [])
    compliant = bible.get("compliant_checks", [])
    
    vendor_identities = {
        "VoltEdge Power Systems": {"class": "VoltEdge", "color": "#0056b3"},
        "Deccan Diesel Co.": {"class": "Deccan", "color": "#e6b800"},
        "CryoCore Climate": {"class": "CryoCore", "color": "#008080"},
        "Trident Switchgear": {"class": "Trident", "color": "#708090"},
        "AegisFire Systems": {"class": "AegisFire", "color": "#cc0000"}
    }
    
    package_map = {
        "VoltEdge UPS, R0": {"eq": "ups", "vendor": "VoltEdge Power Systems", "sec": "26 33 53", "title": "Static UPS", "id": "SUB-263353-01-R0", "rev": "R0"},
        "VoltEdge UPS, R1": {"eq": "ups", "vendor": "VoltEdge Power Systems", "sec": "26 33 53", "title": "Static UPS", "id": "SUB-263353-01-R1", "rev": "R1"},
        "VoltEdge battery cabinet": {"eq": "battery", "vendor": "VoltEdge Power Systems", "sec": "26 33 53", "title": "Battery Energy Storage", "id": "SUB-263353-02-R0", "rev": "R0"},
        "Deccan generator": {"eq": "generator", "vendor": "Deccan Diesel Co.", "sec": "26 32 13", "title": "Engine Generators", "id": "SUB-263213-01-R0", "rev": "R0"},
        "CryoCore CRAH": {"eq": "crah", "vendor": "CryoCore Climate", "sec": "23 81 23", "title": "CRAH Units", "id": "SUB-238123-01-R0", "rev": "R0"},
        "Trident switchgear": {"eq": "switchgear", "vendor": "Trident Switchgear", "sec": "26 13 26", "title": "MV Switchgear", "id": "SUB-261326-01-R0", "rev": "R0"},
        "AegisFire suppression": {"eq": "fire_suppression", "vendor": "AegisFire Systems", "sec": "21 22 00", "title": "Clean Agent System", "id": "SUB-212200-01-R0", "rev": "R0"}
    }
    
    curves_data = {}
    
    def get_custom_submittal_value(pkg, pkey, cval, unit_str, cond):
        if pkg == "Deccan generator":
            if pkey == "standby_rating_kva":
                return "2500 kVA @ 40 deg C"
            elif pkey == "day_tank_capacity_l":
                return "990 L"
        elif pkg == "CryoCore CRAH":
            if pkey == "airflow_m3_h":
                return "62390 m3/h"
            elif pkey == "refrigerant":
                return "R-407C"
        elif pkg == "AegisFire suppression":
            if pkey == "discharge_time_s":
                return "9.2 s"
        elif pkg == "VoltEdge battery cabinet":
            if pkey == "nominal_capacity":
                return "550 kWh (1145.8 Ah)"
            elif pkey == "operating_temperature_range":
                return "0C to 20C"
        return fmt_claimed_val(cval, unit_str)

    for pkg_name, meta in package_map.items():
        status = submittals.get(pkg_name, {}).get("status", "ACTIVE")
        eq_key = meta["eq"]
        vendor_name = meta["vendor"]
        vid = vendor_identities[vendor_name]
        
        # Collect checks for this package
        pkg_devs = [d for d in deviations if d.get("package") == pkg_name]
        pkg_comps = [c for c in compliant if c.get("package") == pkg_name]
        all_checks = pkg_devs + pkg_comps
        
        # Load and merge parameters
        merged_params = {}
        if eq_key and eq_key in bible["equipment"]:
            merged_params = copy.deepcopy(bible["equipment"][eq_key]["parameters"])
            
        # Overrides from submittal package
        pkg_data = bible["submittal_packages"].get(pkg_name, {})
        overrides = pkg_data.get("parameter_overrides", {})
        for p_key, o_data in overrides.items():
            if p_key in merged_params:
                merged_params[p_key].update(o_data)
            else:
                merged_params[p_key] = o_data
                
        # Map parameter key -> spec_clause (e.g. from checks for this package)
        pkg_param_clauses = {}
        for chk in all_checks:
            pk = check_to_param.get(chk["check_id"])
            if pk:
                pkg_param_clauses[pk] = chk["spec_clause"]
                
        # Dynamically determine where_expressed overrides from checks
        param_where_expressed = {}
        for chk in all_checks:
            pk = check_to_param.get(chk["check_id"])
            if pk and chk.get("where_expressed"):
                param_where_expressed[pk] = chk.get("where_expressed")
        # Specific override for AegisFire discharge_time_s to ensure it's in the footnote
        if pkg_name == "AegisFire suppression":
            param_where_expressed["discharge_time_s"] = "footnote"
                
        # Build footnotes list
        footnotes = []
        fn_count = 1
        fn_map = {} # maps p_key to footnote index
        
        for p_key, p_data in sorted(merged_params.items()):
            where_expr = param_where_expressed.get(p_key, p_data.get("where_expressed"))
            if where_expr == "footnote":
                claimed_val = p_data["claimed_val"]
                display_name = p_data["display_name"]
                unit = p_data.get("unit")
                claimed_condition = p_data.get("claimed_condition")
                
                # Check if it is a missing parameter
                if claimed_val == "missing":
                    continue
                
                clause_suffix = ""
                
                if isinstance(claimed_val, str) and len(claimed_val.split()) > 3:
                    text = claimed_val + clause_suffix
                else:
                    val_str = get_custom_submittal_value(pkg_name, p_key, claimed_val, unit, claimed_condition)
                    cond = f" ({claimed_condition})" if claimed_condition and claimed_condition != "standard" else ""
                    text = f"{display_name} is {val_str}{cond}{clause_suffix}"
                    
                footnotes.append({"num": fn_count, "text": text})
                fn_map[p_key] = fn_count
                fn_count += 1
                
        # Build datasheet rows
        datasheet_rows = []
        for p_key, p_data in sorted(merged_params.items()):
            where_expr = param_where_expressed.get(p_key, p_data.get("where_expressed"))
            if where_expr == "main table":
                claimed_val = p_data["claimed_val"]
                display_name = p_data["display_name"]
                unit = p_data.get("unit")
                claimed_condition = p_data.get("claimed_condition")
                
                if claimed_val == "missing":
                    continue
                
                name = display_name
                val = get_custom_submittal_value(pkg_name, p_key, claimed_val, unit, claimed_condition)
                
                # Check for footnote link
                fn_num = None
                footnote_key = f"{p_key}_footnote"
                if footnote_key in fn_map:
                    fn_num = fn_map[footnote_key]
                elif p_key == "discharge_time_s":
                    fn_num = fn_map.get("discharge_time_footnote")
                    
                datasheet_rows.append({"name": name, "value": val, "footnote": fn_num})
                
                # Double capacity rows for battery cabinet to fulfill both shortfall and unit checks
                if pkg_name == "VoltEdge battery cabinet" and p_key == "nominal_capacity":
                    datasheet_rows.append({"name": "Rated Battery Bank Capacity", "value": "576 kWh (1200 Ah)", "footnote": None})
                
        # Reviewed Spec Revision for transmittal
        spec_revision = "Rev 2024"
        if "spec_revision" in merged_params:
            spec_revision = merged_params["spec_revision"]["claimed_val"]
                
        # Compliance Matrix
        # Default response is Comply
        # If check maps to a compliance matrix parameter, Response shows claimed_val
        check_to_param_key = {
            "DEV-UPS-R0-CERT": "certification",
            "DEV-GEN-OBS-CERT": "generator_controller",
            "DEV-GEN-AMB-VENT": "room_ventilation",
            "DEV-FIRE-STD-OBS": "standard_edition_compliance",
            "DEV-FIRE-HOLDTIME": "hold_time_min",
            "DEV-FIRE-STANDARDS": "cylinder_certification_standard",
            "COMP-UPS-R1-CERT": "certification"
        }
        
        matrix_rows = []
        for chk in all_checks:
            resp = chk.get("vendor_response", "Comply")
            cid = chk["check_id"]
            if cid in check_to_param_key:
                pk = check_to_param_key[cid]
                if pk in merged_params:
                    if cid == "DEV-FIRE-HOLDTIME":
                        resp = "9 minutes"
                    elif cid in ["DEV-UPS-R0-CERT", "COMP-UPS-R1-CERT"]:
                        resp = "IEC 62040-3"
                    else:
                        resp = fmt_claimed_val(merged_params[pk]["claimed_val"], merged_params[pk].get("unit"))
            matrix_rows.append({
                "clause_id": chk["spec_clause"],
                "text": get_clause_text(bible, chk["spec_clause"]),
                "response": resp
            })
            
        matrix_pages = []
        for i in range(0, len(matrix_rows), 10):
            matrix_pages.append(matrix_rows[i:i+10])
            
        # Curves
        perf_curves = []
        if pkg_name in ["VoltEdge UPS, R0", "VoltEdge UPS, R1"]:
            if pkg_name == "VoltEdge UPS, R0":
                x_vals, y_vals = [25, 50, 75, 100], [92.0, 95.1, 96.0, 96.2]
            else:
                x_vals, y_vals = [25, 50, 75, 100], [92.0, 96.2, 96.0, 96.2]
            c_data = create_plot("Efficiency vs Load", "Load (%)", "Efficiency (%)", x_vals, y_vals)
            perf_curves.append({"image_data": c_data})
            curves_data[pkg_name] = {"x": x_vals, "y": y_vals}
        elif pkg_name == "Deccan generator":
            x_vals, y_vals = [30, 35, 40, 45, 50], [2500, 2500, 2500, 2450, 2375]
            c_data = create_plot("Derating vs Ambient", "Ambient (C)", "Rating (kVA)", x_vals, y_vals)
            perf_curves.append({"image_data": c_data})
            curves_data[pkg_name] = {"x": x_vals, "y": y_vals}
            
        cert_included = True
        if any(d["check_id"] == "DEV-FIRE-CERT-MISS" for d in pkg_devs):
            cert_included = False
            
        total_pages = 2 + (1 if perf_curves else 0) + len(matrix_pages) + (1 if cert_included else 0)
        
        template = env.get_template("submittal.html")
        html_str = template.render(
            vendor_class=vid["class"], vendor_name=vendor_name,
            submittal_id=meta["id"], package_title=meta["title"],
            spec_section=meta["sec"], revision=meta["rev"], date="01-01-2025",
            status=status,
            spec_revision=spec_revision,
            datasheet_rows=datasheet_rows,
            footnotes=footnotes,
            performance_curves=perf_curves,
            compliance_matrix_pages=matrix_pages,
            certificate_included=cert_included,
            total_pages=total_pages
        )
        out_pdf = os.path.join(RENDERED_DIR, f"{meta['id']}.pdf")
        render_pdf(html_str, out_pdf)
        labels_cache[out_pdf.split('/')[-1]] = extract_text_pypdf(out_pdf)
        print(f"Generated {out_pdf}")
        
    with open(os.path.join(RENDERED_DIR, "curves_data.json"), "w") as f:
        json.dump(curves_data, f, indent=2)
    print("Exported curves_data.json")

def build_labels(bible, labels_cache):
    all_checks = bible.get("deviations", []) + bible.get("compliant_checks", [])
    defects = bible.get("spec_defects", [])
    
    # Pre-build parameter overrides for all packages to find where_expressed
    package_map = {
        "VoltEdge UPS, R0": {"eq": "ups"},
        "VoltEdge UPS, R1": {"eq": "ups"},
        "VoltEdge battery cabinet": {"eq": "battery"},
        "Deccan generator": {"eq": "generator"},
        "CryoCore CRAH": {"eq": "crah"},
        "Trident switchgear": {"eq": "switchgear"},
        "AegisFire suppression": {"eq": "fire_suppression"}
    }
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

    labels_json = []
    
    # Mapping for submittals
    package_to_pdf = {
        "VoltEdge UPS, R0": "SUB-263353-01-R0.pdf",
        "VoltEdge UPS, R1": "SUB-263353-01-R1.pdf",
        "VoltEdge battery cabinet": "SUB-263353-02-R0.pdf",
        "Deccan generator": "SUB-263213-01-R0.pdf",
        "CryoCore CRAH": "SUB-238123-01-R0.pdf",
        "Trident switchgear": "SUB-261326-01-R0.pdf",
        "AegisFire suppression": "SUB-212200-01-R0.pdf"
    }
    
    for chk in all_checks:
        cid = chk["check_id"]
        clause = chk["spec_clause"]
        sec = clause[:8].replace(" ", "_")
        spec_pdf = f"{sec}.pdf"
        
        # Spec page
        spage = find_page_for_regex(labels_cache[spec_pdf], re.escape(clause))
        
        # Submittal page
        sub_pdf = package_to_pdf.get(chk["package"])
        subpage = 0
        
        # Determine where_expressed dynamically
        pkg_name = chk.get("package")
        pk = check_to_param.get(cid)
        where_expr = chk.get("where_expressed")
        if not where_expr:
            if pk and pkg_name in pkg_params and pk in pkg_params[pkg_name]:
                where_expr = pkg_params[pkg_name][pk].get("where_expressed")
        if not where_expr:
            where_expr = "main table"
            
        # Specific override for AegisFire discharge_time_s
        if pkg_name == "AegisFire suppression" and pk == "discharge_time_s":
            where_expr = "footnote"
            
        if sub_pdf:
            if where_expr == "curve":
                subpage = 3
            else:
                subpage = find_page_for_regex(labels_cache[sub_pdf], re.escape(clause))
                if not subpage:
                    subpage = 2 # fallback to datasheet
                    
        labels_json.append({
            "check_id": cid,
            "package": chk.get("package", ""),
            "spec_clause": clause,
            "deviation_type": chk.get("deviation_type", ""),
            "tier": chk.get("tier", ""),
            "verdict_pre_addendum": chk["verdict_pre_addendum"],
            "verdict_post_addendum": chk["verdict_post_addendum"],
            "explanation": chk["explanation"],
            "where_expressed": where_expr,
            "spec_pdf": spec_pdf,
            "spec_page": spage,
            "submittal_pdf": sub_pdf,
            "submittal_page": subpage
        })
        
    for d in defects:
        cid = d["defect_id"]
        sec = d["section"].replace(" ", "_")
        spec_pdf = f"{sec}.pdf"
        # We need a page, find by clause ID matching the section
        loc_str = d.get("location", "")
        matches = re.findall(r'(\d{2} \d{2} \d{2}\s+Part\s+[\d\.A-Za-z]+)', loc_str)
        snippet = loc_str.split("vs")[0].strip() # fallback
        for m in matches:
            if m.startswith(d["section"]):
                snippet = m
                break
                
        spage = find_page_for_regex(labels_cache[spec_pdf], re.escape(snippet.split("Part")[-1].strip()))
        if not spage:
            spage = 1
            
        labels_json.append({
            "check_id": cid,
            "package": "",
            "spec_clause": d.get("location", ""),
            "deviation_type": "defect",
            "tier": "",
            "verdict_pre_addendum": "",
            "verdict_post_addendum": "",
            "explanation": d["description"],
            "spec_pdf": spec_pdf,
            "spec_page": spage,
            "submittal_pdf": "",
            "submittal_page": 0
        })

    with open(LABELS_PATH, "w") as f:
        json.dump(labels_json, f, indent=2)
    print(f"Exported {LABELS_PATH} with {len(labels_json)} entries")

def main():
    os.makedirs(RENDERED_DIR, exist_ok=True)
    with open(BIBLE_PATH, "r") as f:
        bible = yaml.safe_load(f)
        
    labels_cache = {}
    export_csvs(bible)
    generate_specs(bible, labels_cache)
    build_addendum(bible, labels_cache)
    build_dbr(labels_cache)
    build_fillers(labels_cache)
    generate_submittals(bible, labels_cache)
    build_labels(bible, labels_cache)
    
if __name__ == "__main__":
    main()
