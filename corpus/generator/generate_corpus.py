import yaml
import os
import subprocess
import csv
import json
from jinja2 import Environment, FileSystemLoader
from pypdf import PdfReader

# Paths
BIBLE_PATH = "corpus/bible/project_bible.yaml"
TEMPLATES_DIR = "corpus/templates"
RENDERED_DIR = "corpus/rendered"
LABELS_DIR = "corpus/labels"
CHROME_PATH = "/home/ananth/.local/bin/google-chrome"

def load_bible():
    with open(BIBLE_PATH, "r") as f:
        return yaml.safe_load(f)

def run_chrome_pdf(input_html, output_pdf):
    # Absolute paths are best for Chrome headless
    abs_input = os.path.abspath(input_html)
    abs_output = os.path.abspath(output_pdf)
    
    cmd = [
        CHROME_PATH,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--print-to-pdf-no-header", # removes chrome header/footers to use our absolute footer
        f"--print-to-pdf={abs_output}",
        abs_input
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error printing {input_html} to PDF:")
        print(result.stderr)
    else:
        print(f"Rendered: {output_pdf}")

def generate_dbr(env, bible):
    template = env.get_template("dbr.html")
    doc_no = "DBR-2026-001-R0"
    html_content = template.render(
        project=bible["project"],
        doc_no=doc_no,
        title="Design Basis Report"
    )
    
    html_path = os.path.join(RENDERED_DIR, "dbr.html")
    pdf_path = os.path.join(RENDERED_DIR, "dbr.pdf")
    
    with open(html_path, "w") as f:
        f.write(html_content)
        
    run_chrome_pdf(html_path, pdf_path)
    return pdf_path

def generate_specs(env, bible):
    template = env.get_template("spec.html")
    
    specs_data = {
        "26 05 00": {
            "title": "Common Electrical Requirements",
            "summary": "This section specifies the common requirements, quality assurance, submittal procedures, and certification standards for all Division 26 electrical work. Other sections in Division 26 point to this section as the central reference hub.",
            "references": [
                "IS 732 - Code of practice for electrical wiring installations",
                "IS 3043 - Code of practice for earthing",
                "IS 1646 - Code of practice for fire safety of buildings (general)",
                "IEC 62040-3 - Uninterruptible power systems (UPS) - Method of specifying performance"
            ],
            "performance": {
                "general_testing": "All electrical equipment must be type-tested. Independent ASTA/KEMA certificates are mandated for medium voltage gear as specified in Part 1.4.3.B.",
                "submittal_procedures": "Submittal files must be uploaded in searchable PDF format and include a compliance matrix."
            },
            "execution": {
                "grounding": "Verify all earthing connections are tight. Measure loop resistance using calibrated earth tester.",
                "quality_control": "Contractor must perform certified field tests prior to final inspection."
            }
        },
        "26 33 53": {
            "title": "Static Uninterruptible Power Supply (UPS)",
            "summary": "This section specifies the technical requirements for static, double-conversion online uninterruptible power supply (UPS) modules to serve the critical IT load.",
            "references": [
                "IEC 62040-3 - Uninterruptible power systems (UPS) - Performance",
                "UL 1778 - Standard for Uninterruptible Power Systems",
                "IS 16242 - Static Uninterruptible Power Systems"
            ],
            "performance": {
                "efficiency": "UPS module double-conversion efficiency must be >= 96.0% at 50%, 75%, and 100% load points under online VFI mode.",
                "redundancy": "UPS modules must be configured as N+1 parallel redundant per group.",
                "battery_runtime": "Batteries must support a minimum of 10.0 minutes of autonomous runtime at 100% rated module load.",
                "input_thd": "Input current Total Harmonic Distortion (THDi) must be <= 5.0% at full load."
            },
            "execution": {
                "efficiency_verification": "Conduct load bank testing to verify efficiency is >= 96.0% (and >= 96.5% after Addendum 3) at all load points.",
                "battery_discharge": "Verify battery autonomous runtime is >= 10 minutes at full load."
            },
            "inject_defects": ["DEF-001", "DEF-002"]
        },
        "26 32 13": {
            "title": "Engine Generators",
            "summary": "This section specifies standby diesel generator sets, control panels, local fuel day tanks, and auxiliary systems for critical power backup.",
            "references": [
                "ISO 8528-5 - Reciprocating internal combustion engine driven AC generator sets",
                "BS 5514 - Reciprocating internal combustion engines",
                "IS 10000 - Methods of tests for internal combustion engines",
                "NFPA 110 - Standard for Emergency and Standby Power Systems"
            ],
            "performance": {
                "standby_rating": "Standby rating must be >= 2500 kVA (2000 kWe) at 0.8 PF. Site ratings must be verified at the project design basis ambient of 45°C.",
                "fuel_autonomy": "Bulk fuel storage must support 48 hours of continuous operation at full load.",
                "day_tank": "Day tanks must support a minimum of 2.0 hours of continuous operation at full load (requires 1040 L).",
                "block_load": "Generator must accept 100% block load in a single step per ISO 8528-5 G3 class."
            },
            "execution": {
                "startup_tests": "Perform initial start and transient load block acceptance testing.",
                "room_ventilation": "Verify room ventilation is adequate to prevent engine overheating."
            },
            "inject_defects": ["DEF-005", "DEF-007"]
        },
        "26 13 26": {
            "title": "Medium Voltage (MV) Switchgear",
            "summary": "This section specifies metal-clad, air-insulated switchgear for primary distribution at 11kV nominal utility voltage.",
            "references": [
                "IEC 62271-200 - AC metal-clad switchgear and controlgear for rated voltages above 1kV",
                "IEC 62271-1 - High-voltage switchgear and controlgear common specifications",
                "IS 3427 - AC metal-clad switchgear and controlgear for voltages above 1kV"
            ],
            "performance": {
                "rated_voltage": "Rated maximum voltage must be >= 12 kV.",
                "bus_current": "Continuous main busbar current rating must be >= 2000 A.",
                "short_circuit": "Short-time withstand rating must be >= 31.5 kA for 3 seconds.",
                "protection_rating": "Enclosure degree of protection must be IP4X (outer cover) and IP2X (internal partitions).",
                "arc_classification": "Internal Arc Classification (IAC) must be AFLR, rated for 31.5 kA for 1.0 second."
            },
            "execution": {
                "dielectric_tests": "Conduct power frequency withstand and lightning impulse voltage testing.",
                "contact_resistance": "Measure busbar joint contact resistances using micro-ohmmeter."
            },
            "inject_defects": ["DEF-003"]
        },
        "23 81 23": {
            "title": "CRAH / Cooling Units",
            "summary": "This section specifies chilled water perimeter computer room air handlers (CRAH) with EC fans for server hall thermal management.",
            "references": [
                "AHRI 1360 - Performance rating of computer room air conditioners",
                "ASHRAE 90.1 - Energy standard for buildings",
                "IS 1391 - Room air conditioners"
            ],
            "performance": {
                "sensible_cooling": "CRAH sensible cooling capacity must be >= 250 kW at 10°C entering chilled water temp.",
                "airflow": "Volumetric airflow rate must be >= 64,320 m3/h (approx. 37,850 CFM).",
                "water_delta": "Chilled water temperature drop (Entering to Leaving) must be 8 K.",
                "efficiency": "EC fan power density must be < 0.10 W/(m3/h) at design operating point.",
                "refrigerant": "Cooling coil circuit must utilize R-410A refrigerant."
            },
            "execution": {
                "airflow_checks": "Measure fan airflow using duct traverse traverse method.",
                "capacity_runs": "Conduct steady-state heat load run to verify sensible cooling capacity."
            },
            "inject_defects": ["DEF-004"]
        },
        "21 22 00": {
            "title": "Clean Agent Fire Suppression",
            "summary": "This section specifies engineered gaseous clean agent fire suppression systems, detection controls, and release valves for server rooms.",
            "references": [
                "NFPA 2001 - Standard on Clean Agent Fire Extinguishing Systems",
                "UL 2166 - Standard for Halocarbon Clean Agent Extinguishing System Units",
                "IS 15493 - Gaseous fire extinguishing systems"
            ],
            "performance": {
                "agent": "Gaseous suppressant agent must be FK-5-1-12 (3M Novec 1230).",
                "discharge_time": "Agent discharge must complete within 10.0 seconds or less.",
                "hold_time": "Agent design concentration must be retained in the protected hazard zone for >= 10 minutes.",
                "safety": "Design concentration must maintain an acceptable safety margin below the NOAEL limit (10.0%)."
            },
            "execution": {
                "door_fan_test": "Perform room integrity door fan testing to verify agent retention hold time.",
                "discharge_test": "Conduct puff testing with nitrogen to verify piping nozzle flow."
            },
            "inject_defects": ["DEF-006"]
        }
    }
    
    spec_paths = {}
    for section, data in specs_data.items():
        # Map spec defects to this section
        defects = []
        for def_id in data.get("inject_defects", []):
            for d in bible["spec_defects"]:
                if d["defect_id"] == def_id:
                    defects.append(d)
                    
        html_content = template.render(
            project=bible["project"],
            section=section,
            section_title=data["title"],
            part1_summary=data["summary"],
            references=data["references"],
            part2_performance=data["performance"],
            part3_execution=data["execution"],
            spec_defects_injected=defects,
            revision="2024",
            rev_date="December 12, 2024",
            title=f"Section {section} - {data['title']}"
        )
        
        file_base = section.replace(" ", "_")
        html_path = os.path.join(RENDERED_DIR, f"spec_{file_base}.html")
        pdf_path = os.path.join(RENDERED_DIR, f"spec_{file_base}.pdf")
        
        with open(html_path, "w") as f:
            f.write(html_content)
            
        run_chrome_pdf(html_path, pdf_path)
        spec_paths[section] = pdf_path
        
    return spec_paths

def generate_submittals(env, bible):
    template = env.get_template("submittal_pkg.html")
    
    submittal_pkgs = [
        {
            "pkg_name": "VoltEdge UPS, R0",
            "transmittal_no": "SUB-263353-001-R0",
            "spec_section": "26 33 53",
            "vendor": "VoltEdge Power Systems",
            "model": "VoltEdge PX-1200",
            "description": "VoltEdge PX-1200 Double Conversion Static UPS Module",
            "qty": 24,
            "stamp": "REVISE AND RESUBMIT",
            "stamp_class": "stamp-revise-resubmit",
            "datasheet_intro": "The VoltEdge PX-1200 is a high-power, transformerless double-conversion online UPS system engineered for high efficiency in hyperscale data center projects. It supports parallel operations for capacity and redundancy.",
            "parameters": bible["equipment"]["ups"]["parameters"],
            "footnote_text": "1. Continuous operation temperature: 0°C to 40°C. Output voltage regulation: +/- 1.0% steady state.\n2. Inverter efficiency under double conversion mode: 96.2% at 100% load, 96.0% at 75% load.\n3. Efficiency reduces to 95.1% under VFI mode when harmonic filters are active at 50% load."
        },
        {
            "pkg_name": "Deccan generator",
            "transmittal_no": "SUB-263213-001-R0",
            "spec_section": "26 32 13",
            "vendor": "Deccan Diesel Co.",
            "model": "Deccan DD-2500",
            "description": "Deccan DD-2500 Standby Diesel Generator Set",
            "qty": 16,
            "stamp": "REVISE AND RESUBMIT",
            "stamp_class": "stamp-revise-resubmit",
            "datasheet_intro": "The Deccan DD-2500 is a premium standby reciprocating diesel generator set rated for 2500 kVA standby power at 50Hz, 1500 RPM. Designed with robust transient response capabilities conforming to ISO G3 standards.",
            "parameters": bible["equipment"]["generator"]["parameters"],
            "footnote_text": "1. Standby rating is defined at 40°C reference ambient temperature and 0.8 power factor. Sound pressure level is 88 dBA at 1 meter free-field.\n2. Ambient temperature derating: Above 40°C, the generator capacity is subject to the Deccan DD-2500 derating curve, which applies a -2.0% capacity reduction per 1°C ambient temperature rise (giving 2450 kVA capacity at 45°C site ambient)."
        },
        {
            "pkg_name": "CryoCore CRAH",
            "transmittal_no": "SUB-238123-001-R0",
            "spec_section": "23 81 23",
            "vendor": "CryoCore Climate",
            "model": "CryoCore CR-250",
            "description": "CryoCore CR-250 Chilled Water Computer Room Air Handler",
            "qty": 88,
            "stamp": "REVISE AND RESUBMIT",
            "stamp_class": "stamp-revise-resubmit",
            "datasheet_intro": "The CryoCore CR-250 is an advanced perimeter computer room air handler featuring high-efficiency EC fans, copper-aluminum chilled water cooling coils, and proportional modulating 2-way control valves.",
            "parameters": bible["equipment"]["crah"]["parameters"],
            "footnote_text": "1. Sensible cooling capacity is rated at entering water 10°C, leaving water 18°C, entering air dry-bulb temperature 35°C.\n2. Maximum cabinet width is 2450 mm, allowing high airflow path. Fan motor rated power: 7.5 HP (5.6 kW)."
        },
        {
            "pkg_name": "Trident switchgear",
            "transmittal_no": "SUB-261326-001-R0",
            "spec_section": "26 13 26",
            "vendor": "Trident Switchgear",
            "model": "Trident T-2000",
            "description": "Trident T-2000 Metal-Clad Air-Insulated MV Switchgear Panels",
            "qty": 10,
            "stamp": "APPROVED",
            "stamp_class": "stamp-approved",
            "datasheet_intro": "The Trident T-2000 is a modular, type-tested metal-clad air-insulated medium voltage switchgear panel rated for 12kV service, continuous bus current of 2000A, and short circuit withstand rating of 31.5kA for 3 seconds.",
            "parameters": bible["equipment"]["switchgear"]["parameters"],
            "footnote_text": "1. Switchgear panel complies fully with IEC 62271-200. Degree of protection is IP4X external, IP2X internal partitions. Internal Arc Classification (IAC) is AFLR rated."
        },
        {
            "pkg_name": "AegisFire suppression",
            "transmittal_no": "SUB-212200-001-R0",
            "spec_section": "21 22 00",
            "vendor": "AegisFire Systems",
            "model": "Aegis CleanAgent ECS-500",
            "description": "Aegis CleanAgent Gaseous Suppression System with FK-5-1-12",
            "qty": 8,
            "stamp": "REVISE AND RESUBMIT",
            "stamp_class": "stamp-revise-resubmit",
            "datasheet_intro": "The Aegis CleanAgent ECS-500 is an engineered gaseous fire extinguishing suppression system designed for the protection of server rooms. It utilizes the clean agent gas FK-5-1-12 stored in high pressure cylinders.",
            "parameters": bible["equipment"]["fire_suppression"]["parameters"],
            "footnote_text": "1. Suppression cylinder working pressure is 360 psi. Agent hold time is 9 minutes (540 seconds).\n2. Gaseous agent discharge completes within 9.2 seconds. Under piping runs exceeding 45 meters, discharge time extends to 11.0 seconds."
        },
        {
            "pkg_name": "VoltEdge UPS, R1",
            "transmittal_no": "SUB-263353-001-R1",
            "spec_section": "26 33 53",
            "vendor": "VoltEdge Power Systems",
            "model": "VoltEdge PX-1200 (Revised)",
            "description": "VoltEdge PX-1200 UPS Module (Revised High Efficiency)",
            "qty": 24,
            "stamp": "APPROVED AS NOTED",
            "stamp_class": "stamp-approved-noted",
            "datasheet_intro": "Revised submittal for the VoltEdge PX-1200 UPS system. It incorporates high-efficiency double-conversion inverter characteristics to meet the updated project design specifications. Note that input THD is now 5.2% due to revised harmonic filter tuning.",
            "parameters": {
                **bible["equipment"]["ups"]["parameters"],
                "efficiency_50_load": {
                    "true_val": 96.2, "spec_val": 96.0, "claimed_val": 96.2,
                    "claimed_condition": "double-conversion mode", "where_expressed": "main table", "unit": "%"
                },
                "input_thd": {
                    "true_val": 5.2, "spec_val": 5.0, "claimed_val": 5.2,
                    "claimed_condition": "at 100% load", "where_expressed": "main table", "unit": "%"
                }
            },
            "footnote_text": "1. Operating ambient dry-bulb temperature limit: 0°C to 40°C.\n2. Inverter efficiency under double conversion mode: 96.2% at 100% load, 96.0% at 75% load, 96.2% at 50% load (without footnote reduction)."
        },
        {
            "pkg_name": "VoltEdge battery cabinet",
            "transmittal_no": "SUB-263353-002-R0",
            "spec_section": "26 33 53",
            "vendor": "VoltEdge Power Systems",
            "model": "VoltEdge BC-200",
            "description": "VoltEdge BC-200 High-Rate VRLA Battery Cabinet Rack",
            "qty": 24,
            "stamp": "REVISE AND RESUBMIT",
            "stamp_class": "stamp-revise-resubmit",
            "datasheet_intro": "The VoltEdge BC-200 is a matching battery cabinet rack housing high-rate Valve Regulated Lead-Acid (VRLA) batteries connected in series to provide DC back-up power to the UPS inverter during utility outages.",
            "parameters": {
                "nominal_energy_kwh": {
                    "true_val": 576.0, "spec_val": 576.0, "claimed_val": 576.0,
                    "claimed_condition": "at 10h discharge rate", "where_expressed": "main table", "unit": "kWh"
                },
                "load_power_factor": {
                    "true_val": 1.0, "spec_val": 1.0, "claimed_val": 0.9,
                    "claimed_condition": "discharge condition", "where_expressed": "footnote", "unit": "dimensionless"
                },
                "dc_bus_voltage": {
                    "true_val": 400.0, "spec_val": 480.0, "claimed_val": 400.0,
                    "claimed_condition": "nominal DC bus", "where_expressed": "main table", "unit": "V"
                },
                "shelf_life_months": {
                    "true_val": "missing", "spec_val": 6.0, "claimed_val": "missing",
                    "claimed_condition": "without recharge", "where_expressed": "missing", "unit": "months"
                },
                "cabinet_weight_kg": {
                    "true_val": 3200.0, "spec_val": 2800.0, "claimed_val": 3200.0,
                    "claimed_condition": "fully loaded", "where_expressed": "main table", "unit": "kg"
                },
                "operating_temp_limit_c": {
                    "true_val": 20.0, "spec_val": 25.0, "claimed_val": 20.0,
                    "claimed_condition": "operating ambient limit", "where_expressed": "main table", "unit": "C"
                },
                "cable_entry_conduit": {
                    "true_val": "bottom", "spec_val": "top_or_bottom", "claimed_val": "bottom",
                    "claimed_condition": "installation config", "where_expressed": "main table", "unit": "text"
                },
                "lvd_contactor_rating": {
                    "true_val": "missing", "spec_val": "continuous", "claimed_val": "missing",
                    "claimed_condition": "standard coil", "where_expressed": "missing", "unit": "text"
                }
            },
            "footnote_text": "1. Cabinet houses 40 blocks of 12V 200Ah batteries in series (nominal DC bus 480VDC). Stated 576 kWh rating is the combined bank nominal capacity rating.\n2. Backup autonomous runtime of 10 minutes is rated under a load power factor condition of 0.9 PF."
        }
    ]
    
    submittal_paths = {}
    for pkg in submittal_pkgs:
        # Filter checks for this package
        package_checks = []
        for c in bible["deviations"]:
            if c["package"] == pkg["pkg_name"]:
                package_checks.append(c)
        for c in bible["compliant_checks"]:
            if c["package"] == pkg["pkg_name"]:
                package_checks.append(c)
                
        # Sort checks by spec clause
        package_checks.sort(key=lambda x: x["spec_clause"])
        
        html_content = template.render(
            project=bible["project"],
            transmittal=pkg,
            vendor=pkg["vendor"],
            model=pkg["model"],
            description=pkg["description"],
            qty=pkg["qty"],
            stamp=pkg["stamp"],
            stamp_class=pkg["stamp_class"],
            datasheet_intro=pkg["datasheet_intro"],
            parameters=pkg["parameters"],
            footnote_text=pkg["footnote_text"],
            package_checks=package_checks,
            title=f"Submittal Package - {pkg['pkg_name']}"
        )
        
        file_base = pkg["pkg_name"].replace(" ", "_").replace(",", "")
        html_path = os.path.join(RENDERED_DIR, f"submittal_{file_base}.html")
        pdf_path = os.path.join(RENDERED_DIR, f"submittal_{file_base}.pdf")
        
        with open(html_path, "w") as f:
            f.write(html_content)
            
        run_chrome_pdf(html_path, pdf_path)
        submittal_paths[pkg["pkg_name"]] = pdf_path
        
    return submittal_paths

def generate_addendum(env, bible):
    template = env.get_template("addendum.html")
    html_content = template.render(
        project=bible["project"],
        changes=bible["addendum_3"]["changes"],
        flips=bible["addendum_3"]["flips"],
        title="Addendum No. 3"
    )
    
    html_path = os.path.join(RENDERED_DIR, "addendum_3.html")
    pdf_path = os.path.join(RENDERED_DIR, "addendum_3.pdf")
    
    with open(html_path, "w") as f:
        f.write(html_content)
        
    run_chrome_pdf(html_path, pdf_path)
    return pdf_path

def generate_fillers(env, bible):
    # Minutes 1, Minutes 2, Method Statement, Change Order
    # Meeting Minutes 1
    template_min = env.get_template("minutes.html")
    m1_content = template_min.render(
        project=bible["project"],
        date="February 5, 2026",
        time="10:00 AM - 11:30 AM",
        subject="Project Kick-off Meeting & Engineering Modularity Review",
        doc_no="MOM-2026-01-R0",
        intro_text="The kick-off meeting aligned the team on the overall project schedule, PUE targets, and modular engineering blocks. The consultant presented the 4 independent server hall layout basis.",
        items=[
            {"no": "1.1", "topic": "IT Load Distribution", "description": "Confirmed IT load is distributed equally as 5MW per hall across 4 halls.", "owner": "All", "date": "Resolved"},
            {"no": "1.2", "topic": "UPS Redundancy", "description": "Agreed that each hall shall have a dedicated 6-module N+1 UPS system.", "owner": "EPC Electrical", "date": "Resolved"},
            {"no": "1.3", "topic": "Cooling Regime", "description": "Chilled water temperatures set to 10°C entering / 18°C leaving. CRAH airflow basis checked.", "owner": "EPC Mech", "date": "Resolved"}
        ],
        title="Meeting Minutes - Kick-off"
    )
    
    m1_html = os.path.join(RENDERED_DIR, "filler_minutes_kickoff.html")
    m1_pdf = os.path.join(RENDERED_DIR, "filler_minutes_kickoff.pdf")
    with open(m1_html, "w") as f: f.write(m1_content)
    run_chrome_pdf(m1_html, m1_pdf)
    
    # Meeting Minutes 2
    m2_content = template_min.render(
        project=bible["project"],
        date="March 10, 2026",
        time="2:00 PM - 3:30 PM",
        subject="UPS R0 Submittal Review Coordination",
        doc_no="MOM-2026-02-R0",
        intro_text="Review meeting to address the technical deviations identified in VoltEdge's UPS R0 submittal and coordinate necessary manufacturer modifications.",
        items=[
            {"no": "2.1", "topic": "UPS R0 Rejection", "description": "Review VoltEdge UPS R0. Noted double-conversion efficiency at 50% load drops to 95.1% in footnote, violating the 96.0% spec limit. Package rejected.", "owner": "EPC Lead", "date": "Resolved"},
            {"no": "2.2", "topic": "Resubmittal Plan", "description": "VoltEdge to submit UPS R1 incorporating high-efficiency settings and removing the VFI filter footnote.", "owner": "VoltEdge", "date": "2026-03-15"}
        ],
        title="Meeting Minutes - UPS R0 Review"
    )
    
    m2_html = os.path.join(RENDERED_DIR, "filler_minutes_ups_review.html")
    m2_pdf = os.path.join(RENDERED_DIR, "filler_minutes_ups_review.pdf")
    with open(m2_html, "w") as f: f.write(m2_content)
    run_chrome_pdf(m2_html, m2_pdf)
    
    # Method Statement
    template_ms = env.get_template("method_statement.html")
    ms_content = template_ms.render(
        project=bible["project"],
        title="Method Statement - UPS Rigging"
    )
    ms_html = os.path.join(RENDERED_DIR, "filler_method_statement.html")
    ms_pdf = os.path.join(RENDERED_DIR, "filler_method_statement.pdf")
    with open(ms_html, "w") as f: f.write(ms_content)
    run_chrome_pdf(ms_html, ms_pdf)
    
    # Change Order
    template_co = env.get_template("change_order.html")
    co_content = template_co.render(
        project=bible["project"],
        title="Contract Change Order"
    )
    co_html = os.path.join(RENDERED_DIR, "filler_change_order.html")
    co_pdf = os.path.join(RENDERED_DIR, "filler_change_order.pdf")
    with open(co_html, "w") as f: f.write(co_content)
    run_chrome_pdf(co_html, co_pdf)
    
    return [m1_pdf, m2_pdf, ms_pdf, co_pdf]

def generate_csv_registers(bible):
    # PO register
    po_path = os.path.join(RENDERED_DIR, "po_register.csv")
    with open(po_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["po_number", "equipment_tag", "spec_section", "vendor", "item_description", "value_inr", "order_date", "lead_time_weeks", "delivery_status"])
        for row in bible["registers"]["po_register"]:
            writer.writerow([row["po_number"], row["equipment_tag"], row["spec_section"], row["vendor"], row["item_description"], row["value_inr"], row["order_date"], row["lead_time_weeks"], row["delivery_status"]])
            
    # Schedule
    sch_path = os.path.join(RENDERED_DIR, "schedule.csv")
    with open(sch_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["activity_id", "name", "duration_days", "predecessors", "float_days", "critical_path"])
        for row in bible["registers"]["schedule"]:
            writer.writerow([row["activity_id"], row["name"], row["duration_days"], row["predecessors"], row["float_days"], row["critical_path"]])
            
    # Cx tests
    cx_path = os.path.join(RENDERED_DIR, "cx_test_register.csv")
    with open(cx_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["test_id", "level", "system", "spec_clause", "acceptance_criteria", "status"])
        for row in bible["registers"]["cx_test_register"]:
            writer.writerow([row["test_id"], row["level"], row["system"], row["spec_clause"], row["acceptance_criteria"], row["status"]])
            
    # RFI log
    rfi_path = os.path.join(RENDERED_DIR, "rfi_log.csv")
    with open(rfi_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["rfi_id", "subject", "query", "response", "status"])
        for row in bible["registers"]["rfi_log"]:
            writer.writerow([row["rfi_id"], row["subject"], row["query"], row["response"], row["status"]])

    print("Generated CSV registers successfully.")

def locate_text_in_pdf(pdf_path, text_query):
    # Reads the rendered PDF and finds the page index (1-based) where the text_query appears
    if not os.path.exists(pdf_path):
        return None
    try:
        reader = PdfReader(pdf_path)
        clean_query = " ".join(text_query.replace("-", " ").split()).lower()
        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            clean_text = " ".join(text.replace("-", " ").split()).lower()
            if clean_query in clean_text:
                return page_num + 1
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}")
    return None

def compute_labels(bible, spec_paths, submittal_paths, addendum_path):
    labels = []
    
    # Process deviations
    for d in bible["deviations"]:
        # Find which spec file maps to this spec_clause
        spec_sec = d["spec_clause"].split(" ")[0] + " " + d["spec_clause"].split(" ")[1]
        spec_pdf = spec_paths.get(spec_sec)
        
        # Search for the check_id or clause in spec PDF
        spec_page = locate_text_in_pdf(spec_pdf, spec_sec) if spec_pdf else None
        if not spec_page:
            spec_page = 2 # default fallback
            
        # Find submittal page by searching for rule_id in submittal PDF
        sub_pdf = submittal_paths.get(d["package"])
        sub_page = locate_text_in_pdf(sub_pdf, d["rule_id"]) if sub_pdf else None
        if not sub_page:
            sub_page = 4 # default fallback (Compliance Matrix is page 4)
            
        labels.append({
            "check_id": d["check_id"],
            "package": d["package"],
            "spec_clause": d["spec_clause"],
            "rule_id": d["rule_id"],
            "deviation_type": d["deviation_type"],
            "tier": d["tier"],
            "verdict_pre_addendum": d["verdict_pre_addendum"],
            "verdict_post_addendum": d["verdict_post_addendum"],
            "explanation": d["explanation"],
            "spec_page": spec_page,
            "submittal_page": sub_page
        })
        
    # Process compliant checks
    for c in bible["compliant_checks"]:
        spec_sec = c["spec_clause"].split(" ")[0] + " " + c["spec_clause"].split(" ")[1]
        spec_pdf = spec_paths.get(spec_sec)
        
        spec_page = locate_text_in_pdf(spec_pdf, spec_sec) if spec_pdf else None
        if not spec_page:
            spec_page = 2
            
        sub_pdf = submittal_paths.get(c["package"])
        sub_page = locate_text_in_pdf(sub_pdf, c["rule_id"]) if sub_pdf else None
        if not sub_page:
            sub_page = 4
            
        labels.append({
            "check_id": c["check_id"],
            "package": c["package"],
            "spec_clause": c["spec_clause"],
            "rule_id": c["rule_id"],
            "deviation_type": "none",
            "tier": "none",
            "verdict_pre_addendum": c["verdict_pre_addendum"],
            "verdict_post_addendum": c["verdict_post_addendum"],
            "explanation": c["explanation"],
            "spec_page": spec_page,
            "submittal_page": sub_page
        })
        
    # Write to labels.json
    os.makedirs(LABELS_DIR, exist_ok=True)
    labels_path = os.path.join(LABELS_DIR, "labels.json")
    with open(labels_path, "w") as f:
        json.dump(labels, f, indent=2)
        
    print(f"Generated ground truth labels.json successfully under {labels_path}")

def main():
    print("Starting generation pipeline...")
    os.makedirs(RENDERED_DIR, exist_ok=True)
    
    bible = load_bible()
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    
    # 1. DBR
    print("Rendering Design Basis Report...")
    dbr_pdf = generate_dbr(env, bible)
    
    # 2. Specs
    print("Rendering Specification sections...")
    spec_paths = generate_specs(env, bible)
    
    # 3. Submittals
    print("Rendering Submittal packages...")
    submittal_paths = generate_submittals(env, bible)
    
    # 4. Addendum
    print("Rendering Addendum...")
    addendum_pdf = generate_addendum(env, bible)
    
    # 5. Fillers
    print("Rendering Copilot filler documents...")
    filler_paths = generate_fillers(env, bible)
    
    # 6. CSV Registers
    print("Generating CSV registers...")
    generate_csv_registers(bible)
    
    # 7. Labels JSON with real page numbers
    print("Computing real page numbers and generating labels.json...")
    compute_labels(bible, spec_paths, submittal_paths, addendum_pdf)
    
    print("Pipeline completed successfully!")

if __name__ == "__main__":
    main()
