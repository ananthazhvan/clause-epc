import os

templates = {
    "base_layout.html": """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{{ title }}</title>
    <style>
        @page {
            size: A4;
            margin: 0;
        }
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
        
        :root {
            --primary: #1a365d;
            --primary-light: #2b6cb0;
            --secondary: #4a5568;
            --success: #2f855a;
            --error: #9b2c2c;
            --warning: #c05621;
            --text-dark: #2d3748;
            --text-light: #718096;
            --border-color: #cbd5e0;
            --bg-light: #f7fafc;
        }

        body {
            font-family: 'Outfit', sans-serif;
            color: var(--text-dark);
            margin: 0;
            padding: 0;
            line-height: 1.5;
            background-color: #ffffff;
            font-size: 10.5pt;
        }

        .page {
            width: 210mm;
            height: 297mm;
            padding: 25mm 20mm 25mm 20mm;
            box-sizing: border-box;
            position: relative;
            page-break-after: always;
            background-color: white;
        }

        .header {
            position: absolute;
            top: 12mm;
            left: 20mm;
            right: 20mm;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 8.5pt;
            color: var(--text-light);
            border-bottom: 1.5px solid var(--border-color);
            padding-bottom: 2mm;
        }

        .header .logo {
            font-weight: 700;
            color: var(--primary);
            letter-spacing: 0.5px;
        }

        .footer {
            position: absolute;
            bottom: 12mm;
            left: 20mm;
            right: 20mm;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 8.5pt;
            color: var(--text-light);
            border-top: 1px solid var(--border-color);
            padding-top: 2mm;
        }

        h1, h2, h3, h4 {
            color: var(--primary);
            margin-top: 0;
            font-weight: 600;
        }

        h1 {
            font-size: 24pt;
            line-height: 1.2;
            margin-bottom: 10px;
        }

        h2 {
            font-size: 16pt;
            border-bottom: 1px solid var(--primary);
            padding-bottom: 3px;
            margin-bottom: 12px;
            margin-top: 20px;
        }

        h3 {
            font-size: 12.5pt;
            margin-bottom: 8px;
            margin-top: 15px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 15px;
            font-size: 9.5pt;
        }

        th {
            background-color: var(--primary);
            color: white;
            font-weight: 600;
            text-align: left;
            padding: 6px 8px;
            border: 1px solid var(--primary);
        }

        td {
            padding: 6px 8px;
            border: 1px solid var(--border-color);
        }

        tr:nth-child(even) td {
            background-color: var(--bg-light);
        }

        .footnote {
            font-size: 8pt;
            color: var(--text-light);
            margin-top: 10px;
            line-height: 1.3;
        }

        .stamp {
            position: absolute;
            top: 30mm;
            right: 20mm;
            border: 4px double;
            padding: 8px 15px;
            font-size: 14pt;
            font-weight: 700;
            text-transform: uppercase;
            transform: rotate(-5deg);
            z-index: 100;
            background-color: white;
        }

        .stamp-approved {
            color: var(--success);
            border-color: var(--success);
        }

        .stamp-approved-noted {
            color: var(--warning);
            border-color: var(--warning);
        }

        .stamp-revise-resubmit {
            color: var(--error);
            border-color: var(--error);
        }

        .hidden-anchor {
            font-size: 1px;
            color: transparent;
            position: absolute;
            bottom: 0;
            right: 0;
        }
        
        .alert-box {
            border-left: 4px solid var(--primary-light);
            background-color: var(--bg-light);
            padding: 10px 15px;
            margin-bottom: 15px;
            border-radius: 0 4px 4px 0;
            font-size: 9.5pt;
        }
    </style>
</head>
<body>
    {% block content %}{% endblock %}
</body>
</html>
""",

    "dbr.html": """{% extends "base_layout.html" %}
{% block content %}
<div class="page">
    <div style="height: 60mm;"></div>
    <div style="border-left: 8px solid var(--primary); padding-left: 20px;">
        <div style="font-size: 14pt; font-weight: 600; color: var(--text-light); text-transform: uppercase; letter-spacing: 1px;">Design Basis Report</div>
        <h1 style="font-size: 28pt; margin: 10px 0;">{{ project.name }}</h1>
        <div style="font-size: 12pt; color: var(--text-light); margin-top: 10px;">Phase 1 Campus Build - 20MW IT Load</div>
    </div>
    
    <div style="margin-top: 60mm; border-top: 2px solid var(--primary); padding-top: 15px; font-size: 10pt;">
        <table style="border: none; margin: 0; width: 60%;">
            <tr style="background: none;"><td style="border: none; padding: 4px 0; font-weight: 600; width: 40%;">Client:</td><td style="border: none; padding: 4px 0;">{{ project.client }}</td></tr>
            <tr style="background: none;"><td style="border: none; padding: 4px 0; font-weight: 600;">EPC Contractor:</td><td style="border: none; padding: 4px 0;">{{ project.epc | upper }} Infrastructure</td></tr>
            <tr style="background: none;"><td style="border: none; padding: 4px 0; font-weight: 600;">Consultant:</td><td style="border: none; padding: 4px 0;">{{ project.consultant }}</td></tr>
            <tr style="background: none;"><td style="border: none; padding: 4px 0; font-weight: 600;">Location:</td><td style="border: none; padding: 4px 0;">{{ project.location }}</td></tr>
            <tr style="background: none;"><td style="border: none; padding: 4px 0; font-weight: 600;">Date:</td><td style="border: none; padding: 4px 0;">January 15, 2026</td></tr>
            <tr style="background: none;"><td style="border: none; padding: 4px 0; font-weight: 600;">Document Ref:</td><td style="border: none; padding: 4px 0;">{{ doc_no }}</td></tr>
        </table>
    </div>
    <div class="footer">
        <span>{{ doc_no }}</span>
        <span>Page 1 of 8</span>
    </div>
</div>

<div class="page">
    <div class="header">
        <span class="logo">MERIDIAN DATA CENTRE CAMPUS</span>
        <span>{{ doc_no }}</span>
    </div>
    <h2>1. Executive Summary</h2>
    <p>This Design Basis Report (DBR) establishes the engineering criteria and parameters for the construction of Phase 1 of the Meridian Data Centre Campus, a state-of-the-art facility designed to support high-density IT operations in Navi Mumbai. The facility is designed to meet Uptime Institute Tier III concurrent maintainability requirements, allowing any component of the electrical or mechanical infrastructure to be taken out of service for maintenance without impacting the critical IT load.</p>
    
    <h2>2. Key Project Identity & Stakeholders</h2>
    <ul>
        <li><strong>Project Title:</strong> {{ project.name }}</li>
        <li><strong>Location:</strong> {{ project.location }}, Maharashtra, India (coastal tropical environment)</li>
        <li><strong>Owner / Developer:</strong> {{ project.client }}</li>
        <li><strong>EPC Contractor:</strong> {{ project.epc | upper }}</li>
        <li><strong>Lead Engineering Consultant:</strong> {{ project.consultant }}</li>
    </ul>

    <h2>3. Design Basis Parameters</h2>
    <table style="margin-top: 10px;">
        <thead>
            <tr>
                <th>Design Parameter</th>
                <th>Target Criteria</th>
                <th>Redundancy / Basis</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Total IT Load</td>
                <td>{{ project.design_basis.total_it_load_kw }} kW (20 MW)</td>
                <td>Max continuous IT operating power</td>
            </tr>
            <tr>
                <td>UPS Topology</td>
                <td>Static Online Double Conversion</td>
                <td>{{ project.design_basis.ups_redundancy }} per Group</td>
            </tr>
            <tr>
                <td>Design Ambient Temperature</td>
                <td>{{ project.design_basis.design_ambient_temp_c }}°C Dry Bulb</td>
                <td>Extreme summer condition, Navi Mumbai</td>
            </tr>
            <tr>
                <td>Target Power Usage Effectiveness (PUE)</td>
                <td>&le; {{ project.design_basis.pue_target }}</td>
                <td>At full design load</td>
            </tr>
            <tr>
                <td>Standby Generator Autonomy</td>
                <td>{{ project.design_basis.generator_autonomy_h }} Hours</td>
                <td>Full campus load storage capacity</td>
            </tr>
            <tr>
                <td>Cooling Unit Redundancy</td>
                <td>Chilled Water Perimeter CRAH</td>
                <td>{{ project.design_basis.cooling_redundancy }} per Hall</td>
            </tr>
            <tr>
                <td>Battery Autonomy (UPS)</td>
                <td>{{ project.design_basis.battery_runtime_min }} Minutes</td>
                <td>At 100% rated module load</td>
            </tr>
        </tbody>
    </table>
    <div class="footer">
        <span>{{ doc_no }}</span>
        <span>Page 2 of 8</span>
    </div>
</div>

<div class="page">
    <div class="header">
        <span class="logo">MERIDIAN DATA CENTRE CAMPUS</span>
        <span>{{ doc_no }}</span>
    </div>
    <h2>4. Architectural & Structural Limits</h2>
    <p>The facility is designed for extreme floor loadings to accommodate the heavy weights of double-conversion UPS cabinets and high-rate lead-acid battery cabinets. The structural concrete slab is engineered for a maximum static load limit of <strong>2,800 kg/m²</strong> in the UPS and battery rooms. Battery cabinets exceeding this limit are prohibited.</p>
    
    <h2>5. Environmental Design Parameters</h2>
    <p>Navi Mumbai is characterized by high summer ambient temperatures and high relative humidity (coastal monsoon climate). The cooling infrastructure is sized for a maximum outdoor design dry-bulb temperature of <strong>45°C</strong>.</p>
    <p>Data halls shall be maintained at <strong>23°C &plusmn; 2°C</strong> supply air temperature (cold aisle containment) and relative humidity of 20-80% non-condensing to prevent electrostatic discharge or moisture condensation on server boards.</p>
    <div class="footer">
        <span>{{ doc_no }}</span>
        <span>Page 3 of 8</span>
    </div>
</div>
{% endblock %}
""",

    "spec.html": """{% extends "base_layout.html" %}
{% block content %}
<div class="page">
    <div class="header">
        <span class="logo">MERIDIAN CAMPUS - TECHNICAL SPECIFICATIONS</span>
        <span>Section {{ section }}</span>
    </div>
    <div style="text-align: center; margin-top: 50mm; margin-bottom: 20mm;">
        <div style="font-size: 14pt; font-weight: 600; color: var(--text-light); text-transform: uppercase;">Technical Specifications</div>
        <h1 style="font-size: 26pt; margin: 10px 0;">SECTION {{ section }}</h1>
        <h2 style="font-size: 18pt; border: none; padding: 0; color: var(--text-dark);">{{ section_title | upper }}</h2>
        <div style="font-size: 10pt; color: var(--text-light); margin-top: 30mm;">
            Project: {{ project.name }}<br>
            Navi Mumbai, India<br>
            Revision: {{ revision }} ({{ rev_date }})
        </div>
    </div>
    <div class="footer">
        <span>Section {{ section }}</span>
        <span>Page 1 of 8</span>
    </div>
</div>

<div class="page">
    <div class="header">
        <span class="logo">SECTION {{ section }} - {{ section_title }}</span>
        <span>Rev {{ revision }}</span>
    </div>
    <h2>PART 1 - GENERAL</h2>
    
    <h3>1.1 Summary</h3>
    <p>{{ part1_summary }}</p>
    
    <h3>1.2 References</h3>
    <ul>
        {% for ref in references %}
        <li>{{ ref }}</li>
        {% endfor %}
    </ul>
    
    <h3>1.3 Submittal Requirements</h3>
    <p>A. Contractor shall submit the following for Engineer's approval prior to equipment procurement:</p>
    <ol>
        <li>Product Data: Technical datasheets detailing all electrical and physical parameters, performance curves, and compliance.</li>
        <li>Shop Drawings: Dimensional layouts showing clearance requirements, cabling paths, and weights.</li>
        <li>Compliance Matrix: Clause-by-clause confirmation of conformance. Any deviation must be explicitly noted.</li>
        <li>Factory Test Certificates and Type Test Certifications.</li>
    </ol>
    
    <h3>1.4 Quality Assurance</h3>
    <p>A. Equipment shall be manufactured by a firm specializing in the equipment class with a minimum of twenty (25) years of continuous commercial manufacturing history.</p>
    <p>B. As specified in Section 26 05 00 Part 1.4.3.B, all medium voltage switchgear and high-power electrical components must be supplied with certified test certificates from an internationally recognized independent laboratory (ASTA, KEMA, or equivalent) confirming compliance with IEC standards.</p>
    <div class="footer">
        <span>Section {{ section }}</span>
        <span>Page 2 of 8</span>
    </div>
</div>

<div class="page">
    <div class="header">
        <span class="logo">SECTION {{ section }} - {{ section_title }}</span>
        <span>Rev {{ revision }}</span>
    </div>
    <h2>PART 2 - PRODUCTS</h2>
    
    <h3>2.1 Acceptable Manufacturers</h3>
    <p>A. Subject to compliance with technical requirements, approved manufacturers are limited to the following:</p>
    <ul>
        {% for mfr in manufacturers %}
        <li>{{ mfr }}</li>
        {% endfor %}
    </ul>
    
    <h3>2.2 Performance and Design Requirements</h3>
    {% for title, text in part2_performance.items() %}
    <p><strong>{{ title }}:</strong> {{ text }}</p>
    {% endfor %}
    
    {% if spec_defects_injected %}
    <!-- Injected Spec Defects for compliance testing -->
    <div class="alert-box">
        <strong>Injected Contract Defects (Internal Quality Control Audit Targets):</strong>
        <ul>
            {% for defect in spec_defects_injected %}
            <li><strong>{{ defect.defect_id }}:</strong> {{ defect.description }} (Location: {{ defect.location }})</li>
            {% endfor %}
        </ul>
    </div>
    {% endif %}
    
    <div class="footer">
        <span>Section {{ section }}</span>
        <span>Page 3 of 8</span>
    </div>
</div>

<div class="page">
    <div class="header">
        <span class="logo">SECTION {{ section }} - {{ section_title }}</span>
        <span>Rev {{ revision }}</span>
    </div>
    <h2>PART 3 - EXECUTION</h2>
    
    <h3>3.1 Installation and Examination</h3>
    <p>A. Verify that structural concrete floor slab is fully cured. Verify structural load limit of 2,800 kg/m² is not exceeded in UPS or battery rooms.</p>
    <p>B. Maintain a minimum clear work clearance of 1000 mm in front of all enclosures, and 1200 mm above, in accordance with local Indian Electricity Rules and IEC standards.</p>
    
    <h3>3.2 Field Quality Control and Site Commissioning</h3>
    <p>A. Startup services shall be performed by factory-authorized technicians.</p>
    <p>B. Commissioning tests must be scheduled and carried out in accordance with the project's overall Cx Test Register. Every testing step must map back to a specific specification clause.</p>
    
    {% for step, detail in part3_execution.items() %}
    <p><strong>{{ step }}:</strong> {{ detail }}</p>
    {% endfor %}
    
    <div class="footer">
        <span>Section {{ section }}</span>
        <span>Page 4 of 8</span>
    </div>
</div>
{% endblock %}
""",

    "submittal_pkg.html": """{% extends "base_layout.html" %}
{% block content %}
<!-- Page 1: Transmittal Sheet -->
<div class="page">
    {% if stamp %}
    <div class="stamp {{ stamp_class }}">{{ stamp }}</div>
    {% endif %}
    
    <div style="border: 2px solid var(--primary); padding: 15px; margin-bottom: 20px;">
        <h2 style="margin: 0; text-align: center; border: none; color: var(--primary);">EQUIPMENT SUBMITTAL TRANSMITTAL</h2>
    </div>
    
    <table style="width: 100%; border: none;">
        <tr style="background: none;"><td style="font-weight: 600; width: 25%;">Transmittal No:</td><td>{{ transmittal.no }}</td><td style="font-weight: 600; width: 20%;">Date:</td><td>{{ transmittal.date }}</td></tr>
        <tr style="background: none;"><td style="font-weight: 600;">Project:</td><td>{{ project.name }}</td><td style="font-weight: 600;">Spec Section:</td><td>{{ transmittal.spec_section }}</td></tr>
        <tr style="background: none;"><td style="font-weight: 600;">Vendor:</td><td>{{ vendor }}</td><td style="font-weight: 600;">Revision:</td><td>{{ transmittal.revision }}</td></tr>
        <tr style="background: none;"><td style="font-weight: 600;">Status:</td><td>FOR REVIEW</td><td style="font-weight: 600;">EPC Lead:</td><td>{{ project.epc | upper }} Electrical</td></tr>
    </table>
    
    <h3>Submittal Item Description</h3>
    <p>We submit for engineering review and approval the product datasheet, compliance matrix, and test certifications for the following equipment:</p>
    <table style="width: 100%;">
        <thead>
            <tr>
                <th>Model Number</th>
                <th>Description</th>
                <th>Qty</th>
                <th>Manufacturer</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>{{ model }}</td>
                <td>{{ description }}</td>
                <td>{{ qty }}</td>
                <td>{{ vendor }}</td>
            </tr>
        </tbody>
    </table>
    
    <h3>Review Comments / Action Taken</h3>
    <div style="border: 1px solid var(--border-color); height: 50mm; padding: 10px; background-color: var(--bg-light); font-size: 9.5pt;">
        <strong>Engineering Review Result:</strong> {% if stamp %}{{ stamp }}{% else %}PENDING{% endif %}<br>
        <strong>Comments:</strong><br>
        {% if transmittal.no == "SUB-263353-001-R0" %}
        - UPS Double-conversion efficiency at 50% load drops to 95.1% in footnote 3, failing the spec minimum of 96.0%. Resubmit with compliant module characteristics.<br>
        - Parallel module configuration is N+1, which violates the spec section 2.1.2.A demanding N+2 redundancy.<br>
        - Missing IEC 62040-3 test certificate.
        {% elif transmittal.no == "SUB-263213-001-R0" %}
        - Standby rating is quoted at 40°C reference ambient. Manufacturer derating curve at 45°C site ambient indicates a 2% drop in capacity (2450 kVA), failing the 2500 kVA standby limit.<br>
        - Generator day tank capacity is 990 L, failing the spec minimum of 1040 L (2.0 hours). Note that this is due to local NBC code capping day tanks to <1000 L, which is a code conflict.<br>
        - Standard mismatch: EMCP 3.2 controller is obsolete.
        {% elif transmittal.no == "SUB-238123-001-R0" %}
        - Airflow is 62,390 m³/h, which is 3.0% below the spec requirement of 64,320 m³/h.<br>
        - Dual power supply feed is missing; unit includes single terminal block only.<br>
        - Unit width is 2450 mm, which exceeds structural corridor limit of 2400 mm.
        {% elif transmittal.no == "SUB-212200-001-R0" %}
        - Cylinder valve test certification is completely missing from the submittal package. Status is missing documents.
        {% else %}
        - Approved with no major comments. All values check compliant.
        {% endif %}
    </div>
    
    <div class="footer">
        <span>{{ transmittal.no }}</span>
        <span>Page 1 of 6</span>
    </div>
</div>

<!-- Page 2: Product Datasheet -->
<div class="page">
    <div class="header">
        <span class="logo">{{ vendor | upper }} PRODUCT DATASHEET</span>
        <span>{{ model }}</span>
    </div>
    <h2>Product Datasheet: {{ model }}</h2>
    <p>{{ datasheet_intro }}</p>
    
    <h3>Technical Parameter Specifications</h3>
    <table style="width: 100%;">
        <thead>
            <tr>
                <th>Parameter Name</th>
                <th>Claimed Value</th>
                <th>Claimed Condition</th>
                <th>Spec Limit</th>
            </tr>
        </thead>
        <tbody>
            {% for name, details in parameters.items() %}
            <tr>
                <td>{{ name | replace('_', ' ') | capitalize }}</td>
                <td>{{ details.claimed_val }} {{ details.unit if details.unit != 'text' and details.unit != 'dimensionless' }}</td>
                <td>{{ details.claimed_condition }}</td>
                <td>{{ details.spec_val }} {{ details.unit if details.unit != 'text' and details.unit != 'dimensionless' }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    
    {% if footnote_text %}
    <div class="footnote">
        <strong>Notes:</strong><br>
        {{ footnote_text }}
    </div>
    {% endif %}
    
    <div class="footer">
        <span>{{ transmittal.no }}</span>
        <span>Page 2 of 6</span>
    </div>
</div>

<!-- Page 3: Performance Curves / Charts -->
<div class="page">
    <div class="header">
        <span class="logo">{{ vendor | upper }} PERFORMANCE CURVES</span>
        <span>{{ model }}</span>
    </div>
    <h2>Equipment Performance Curves</h2>
    <p>The following performance characteristic curves are extracted from the factory testing data registry and represent standard operational output limits.</p>
    
    <div style="text-align: center; margin-top: 15mm; margin-bottom: 10mm;">
        {% if "UPS" in model %}
        <img src="assets/ups_efficiency_curve.png" style="width: 120mm; border: 1px solid var(--border-color);" alt="UPS Efficiency Curve">
        {% elif "DD" in model %}
        <img src="assets/gen_derating_curve.png" style="width: 120mm; border: 1px solid var(--border-color);" alt="Generator Derating Curve">
        {% else %}
        <div style="height: 80mm; width: 120mm; border: 1.5px dashed var(--border-color); display: flex; justify-content: center; align-items: center; margin: 0 auto; color: var(--text-light);">
            Performance curve chart not required for this equipment class.
        </div>
        {% endif %}
    </div>
    
    <div class="footnote">
        * Charts generated programmatically from mathematical model of physical properties at design limit.
    </div>
    
    <div class="footer">
        <span>{{ transmittal.no }}</span>
        <span>Page 3 of 6</span>
    </div>
</div>

<!-- Page 4: Compliance Matrix Statement -->
<div class="page">
    <div class="header">
        <span class="logo">{{ vendor | upper }} COMPLIANCE MATRIX</span>
        <span>{{ model }}</span>
    </div>
    <h2>Clause-by-Clause Conformance Statement</h2>
    <p>Below is our conformance statement indicating compliance with each clause of Section {{ transmittal.spec_section }} of the construction specifications.</p>
    
    <table style="width: 100%;">
        <thead>
            <tr>
                <th>Spec Clause</th>
                <th>Parameter / Requirement</th>
                <th>Conformance Claim</th>
                <th>Remarks / Evidence</th>
            </tr>
        </thead>
        <tbody>
            {% for check in package_checks %}
            <tr>
                <td>{{ check.spec_clause }}</td>
                <td>{{ check.rule_id }}</td>
                <td style="font-weight: bold; color: {% if check.verdict_pre_addendum == 'COMPLIANT' %}var(--success){% elif check.verdict_pre_addendum == 'NEEDS_REVIEW' %}var(--warning){% else %}var(--error){% endif %};">
                    {% if check.verdict_pre_addendum == 'COMPLIANT' %}C{% elif check.verdict_pre_addendum == 'NEEDS_REVIEW' %}NEEDS REVIEW{% else %}NC{% endif %}
                </td>
                <td>
                    {% if check.verdict_pre_addendum == 'COMPLIANT' %}
                    Conforms. {{ check.explanation }}
                    {% elif check.verdict_pre_addendum == 'NEEDS_REVIEW' %}
                    Complies, subject to qualitative review of the ventilation and chilled water conditions.
                    {% else %}
                    Non-Conformant. {{ check.explanation }}
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    
    <div class="footer">
        <span>{{ transmittal.no }}</span>
        <span>Page 4 of 6</span>
    </div>
</div>

<!-- Page 5: Test Certificate -->
<div class="page">
    <div class="header">
        <span class="logo">{{ vendor | upper }} TEST CERTIFICATE</span>
        <span>{{ model }}</span>
    </div>
    <div style="border: 2px solid var(--primary); padding: 30px; text-align: center; margin-top: 20mm; background-color: var(--bg-light);">
        <h2 style="color: var(--primary); margin: 0; font-size: 20pt; border: none; padding: 0;">CERTIFICATE OF CONFORMANCE</h2>
        <div style="font-size: 11pt; color: var(--text-light); margin-top: 10px;">Factory Quality Assurance Department</div>
        
        <div style="margin-top: 20mm; font-size: 11pt; text-align: left; line-height: 1.8; padding: 0 10mm;">
            We hereby certify that the equipment listed below has been manufactured, tested, and inspected in accordance with all active factory testing specifications and international standards.<br><br>
            <strong>Equipment Model:</strong> {{ model }}<br>
            <strong>Serial Numbers:</strong> {{ vendor[:3] | upper }}-2026-{{ transmittal.spec_section[:2] }}01 to 08<br>
            <strong>Test Standards:</strong> IEC 62040-3, IEC 62271-200, ISO 8528-5 as applicable.<br>
            <strong>Quality Inspector:</strong> Dr. H. Bose (Director of QA)<br>
            <strong>Date of Inspection:</strong> January 8, 2026
        </div>
        
        <div style="margin-top: 25mm; display: flex; justify-content: space-around; font-size: 10pt;">
            <div>
                <div style="border-top: 1px solid var(--text-dark); width: 40mm; margin: 0 auto;"></div>
                <div style="margin-top: 5px;">Quality Inspector Signature</div>
            </div>
            <div>
                <div style="border-top: 1px solid var(--text-dark); width: 40mm; margin: 0 auto;"></div>
                <div style="margin-top: 5px;">Plant Manager Signature</div>
            </div>
        </div>
    </div>
    
    <div class="footer">
        <span>{{ transmittal.no }}</span>
        <span>Page 5 of 6</span>
    </div>
</div>
{% endblock %}
""",

    "addendum.html": """{% extends "base_layout.html" %}
{% block content %}
<div class="page">
    <div style="border-bottom: 3px solid var(--primary); padding-bottom: 10px; margin-bottom: 20px;">
        <h1 style="margin: 0; font-size: 22pt; color: var(--primary);">ADDENDUM NO. 3</h1>
        <div style="font-size: 10pt; color: var(--text-light);">Project: {{ project.name }} | Navi Mumbai, India</div>
        <div style="font-size: 10pt; color: var(--text-light);">Date: June 15, 2026 | Ref: ADD-003-R0</div>
    </div>
    
    <p>To all prospective bidders, contractors, and vendors, this Addendum is issued to modify and amend the active tender and construction specification documents. The changes detailed below shall supersede the original clauses with immediate effect.</p>
    
    <h2>1. Modifications to Technical Specifications</h2>
    
    {% for change in changes %}
    <div style="border: 1px solid var(--border-color); padding: 15px; margin-bottom: 15px; background-color: var(--bg-light);">
        <div style="font-weight: 600; color: var(--primary); font-size: 11pt; margin-bottom: 5px;">Reference: {{ change.reference }}</div>
        <div style="font-family: monospace; font-size: 10pt; margin: 10px 0; background-color: white; padding: 10px; border-left: 4px solid var(--error);">
            Instruction: {{ change.action }}
        </div>
        <div style="font-size: 9.5pt; color: var(--text-dark);">
            Description: {{ change.description }}
        </div>
    </div>
    {% endfor %}
    
    <h2>2. Impact Summary & Affected Registers</h2>
    <p>Ingestion of Addendum No. 3 shifts the compliance status of several packages, procurement orders, and testing criteria. The affected elements are detailed in the project bible flips directory.</p>
    
    <div class="footer">
        <span>ADD-003</span>
        <span>Page 1 of 2</span>
    </div>
</div>

<div class="page">
    <div class="header">
        <span class="logo">ADDENDUM NO. 3 - MERIDIAN CAMPUS</span>
        <span>ADD-003</span>
    </div>
    <h2>3. Detailed Ingestion Flips (Audit Trails)</h2>
    <table style="width: 100%;">
        <thead>
            <tr>
                <th>Affected Target</th>
                <th>Pre-Addendum Verdict</th>
                <th>Post-Addendum Verdict</th>
                <th>Technical Reason for Flip</th>
            </tr>
        </thead>
        <tbody>
            {% for flip in flips %}
            <tr>
                <td>{{ flip.id }}</td>
                <td style="font-weight: bold; color: var(--success);">{{ flip.before_verdict }}</td>
                <td style="font-weight: bold; color: var(--error);">{{ flip.after_verdict }}</td>
                <td>{{ flip.explanation }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    
    <div class="footer">
        <span>ADD-003</span>
        <span>Page 2 of 2</span>
    </div>
</div>
{% endblock %}
""",

    "minutes.html": """{% extends "base_layout.html" %}
{% block content %}
<div class="page">
    <div style="border-bottom: 2px solid var(--primary); padding-bottom: 10px; margin-bottom: 20px;">
        <h1 style="margin: 0; font-size: 20pt; color: var(--primary);">MEETING MINUTES</h1>
        <div style="font-size: 9.5pt; color: var(--text-light);">Project: {{ project.name }} | Navi Mumbai, India</div>
    </div>
    
    <table style="width: 100%; border: none; margin-bottom: 20px;">
        <tr style="background: none;"><td style="font-weight: 600; width: 20%; border: none;">Meeting Date:</td><td style="border: none;">{{ date }}</td><td style="font-weight: 600; width: 20%; border: none;">Time:</td><td style="border: none;">{{ time }}</td></tr>
        <tr style="background: none;"><td style="font-weight: 600; border: none;">Subject:</td><td style="border: none; font-weight: 600; color: var(--primary-light);">{{ subject }}</td><td style="font-weight: 600; border: none;">Ref No:</td><td style="border: none;">{{ doc_no }}</td></tr>
        <tr style="background: none;"><td style="font-weight: 600; border: none;">Attendees:</td><td style="border: none;" colspan="3">A. Verma (Client), S. Kumar (EPC Lead), R. Sharma (Consultant)</td></tr>
    </table>
    
    <h2>1. Discussion Notes</h2>
    <p>{{ intro_text }}</p>
    
    <h2>2. Key Decisions and Action Items</h2>
    <table style="width: 100%;">
        <thead>
            <tr>
                <th>Item No</th>
                <th>Discussion / Decision</th>
                <th>Action Owner</th>
                <th>Target Date</th>
            </tr>
        </thead>
        <tbody>
            {% for item in items %}
            <tr>
                <td>{{ item.no }}</td>
                <td><strong>{{ item.topic }}:</strong> {{ item.description }}</td>
                <td>{{ item.owner }}</td>
                <td>{{ item.date }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    
    <div class="footer">
        <span>{{ doc_no }}</span>
        <span>Page 1 of 1</span>
    </div>
</div>
{% endblock %}
""",

    "method_statement.html": """{% extends "base_layout.html" %}
{% block content %}
<div class="page">
    <div style="border-bottom: 2px solid var(--primary); padding-bottom: 10px; margin-bottom: 20px;">
        <h1 style="margin: 0; font-size: 20pt; color: var(--primary);">METHOD STATEMENT</h1>
        <div style="font-size: 9.5pt; color: var(--text-light);">Project: {{ project.name }} | Navi Mumbai, India</div>
    </div>
    
    <table style="width: 100%; border: none; margin-bottom: 20px;">
        <tr style="background: none;"><td style="font-weight: 600; width: 25%; border: none;">Document No:</td><td style="border: none;">MS-263353-01-R0</td><td style="font-weight: 600; width: 20%; border: none;">Date:</td><td style="border: none;">February 20, 2026</td></tr>
        <tr style="background: none;"><td style="font-weight: 600; border: none;">Title:</td><td style="border: none; font-weight: 600; color: var(--primary-light);">UPS Systems Rigging & Position Method Statement</td><td style="font-weight: 600; border: none;">Author:</td><td style="border: none;">EPC Rigging Crew</td></tr>
    </table>
    
    <h2>1. Scope of Work</h2>
    <p>This method statement outlines the safe unloading, rigging, positioning, and anchoring of the VoltEdge PX-1200 UPS modules and associated battery cabinet racks inside the UPS Room in the first server hall. The weights of the equipment are massive and require structural layout audits prior to lift.</p>
    
    <h2>2. Health, Safety and Structural Limits</h2>
    <ul>
        <li><strong>Structural Floor Load Capacity:</strong> Static load limit of 2,800 kg/m² must not be exceeded. Heavy loaded battery cabinets (3200 kg) must be moved using heavy-duty steel path-spreaders to avoid local shear failure of the concrete slab.</li>
        <li><strong>PPE:</strong> Safety shoes, steel-toe, hard hat, safety glasses, and high-visibility jackets are mandatory during all rigging phases.</li>
    </ul>
    
    <h2>3. Step-by-Step Procedure</h2>
    <ol>
        <li>Perform pre-lift safety meeting with crane operators and riggers.</li>
        <li>Inspect UPS room concrete floor to verify it is fully cured and free of cracks.</li>
        <li>Lay 12mm thick steel spreader plates along the transit path from unloading bay to UPS room.</li>
        <li>Rig and lift VoltEdge UPS module using spreader beams to crane hooks.</li>
        <li>Position on plinth and secure using M16 expansion anchor bolts.</li>
    </ol>
    
    <div class="footer">
        <span>MS-263353-01</span>
        <span>Page 1 of 1</span>
    </div>
</div>
{% endblock %}
""",

    "change_order.html": """{% extends "base_layout.html" %}
{% block content %}
<div class="page">
    <div style="border-bottom: 2px solid var(--primary); padding-bottom: 10px; margin-bottom: 20px;">
        <h1 style="margin: 0; font-size: 20pt; color: var(--primary);">CONTRACT CHANGE ORDER</h1>
        <div style="font-size: 9.5pt; color: var(--text-light);">Project: {{ project.name }} | Navi Mumbai, India</div>
    </div>
    
    <table style="width: 100%; border: none; margin-bottom: 20px;">
        <tr style="background: none;"><td style="font-weight: 600; width: 25%; border: none;">Change Order No:</td><td style="border: none;">CO-003-R0</td><td style="font-weight: 600; width: 20%; border: none;">Date:</td><td style="border: none;">June 20, 2026</td></tr>
        <tr style="background: none;"><td style="font-weight: 600; border: none;">Title:</td><td style="border: none; font-weight: 600; color: var(--primary-light);">UPS Efficiency & CRAH Design Water Temp Modification</td><td style="font-weight: 600; border: none;">EPC Lead:</td><td style="border: none;">S. Kumar</td></tr>
    </table>
    
    <h2>1. Description of Change</h2>
    <p>This Change Order is issued to adjust the contract commercial basis in accordance with Addendum No. 3, which increased the static UPS efficiency requirement to 96.5% and revised the entering chilled water temperature to 11°C. This changes the pricing and procurement structure of the active POs.</p>
    
    <h2>2. Cost and Schedule Impact</h2>
    <table style="width: 100%;">
        <thead>
            <tr>
                <th>Item</th>
                <th>Original Cost (INR)</th>
                <th>Variation Cost (INR)</th>
                <th>New Cost (INR)</th>
                <th>Schedule Impact</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>VoltEdge UPS Re-procurement</td>
                <td>₹10.00 Crore</td>
                <td>₹1.50 Crore</td>
                <td>₹11.50 Crore</td>
                <td>0 Days (No delay)</td>
            </tr>
            <tr>
                <td>CryoCore CRAH Engineering Re-sizing</td>
                <td>₹1.40 Crore</td>
                <td>₹0.20 Crore</td>
                <td>₹1.60 Crore</td>
                <td>0 Days (No delay)</td>
            </tr>
        </tbody>
    </table>
    
    <h2>3. Approvals</h2>
    <p>All other terms of the original EPC agreement remain unchanged. Work on these variations is authorized to proceed immediately.</p>
    
    <div class="footer">
        <span>CO-003</span>
        <span>Page 1 of 1</span>
    </div>
</div>
{% endblock %}
"""
}

def write_templates():
    os.makedirs("corpus/templates", exist_ok=True)
    for name, content in templates.items():
        path = os.path.join("corpus/templates", name)
        with open(path, "w") as f:
            f.write(content)
        print(f"Wrote template: {path}")

if __name__ == "__main__":
    write_templates()
