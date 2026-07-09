#!/usr/bin/env python3
"""
Build the clause registry for project_bible.yaml.
Appends a top-level 'clauses:' block containing full CSI 3-part
specification text for all 6 sections.

Defects DEF-001 through DEF-007 are embedded as natural clause text.
Cross-references between sections are added where appropriate.
"""

import os
import sys
import yaml

BIBLE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "project_bible.yaml")


def p(cid, text, **kwargs):
    """Create a paragraph (clause) entry."""
    entry = {"clause_id": cid, "text": text}
    entry.update(kwargs)
    return entry


def build_26_05_00():
    """Section 26 05 00 - Common Work Results for Electrical."""
    S = "26 05 00"
    return {
        "title": "Common Work Results for Electrical",
        "parts": [
            {
                "part": 1,
                "title": "GENERAL",
                "articles": [
                    {
                        "number": "1.1",
                        "title": "Summary",
                        "paragraphs": [
                            p(f"{S} Part 1.1.1.A",
                              "This section specifies the general electrical requirements common to all "
                              "electrical specification sections for the Meridian Data Centre Campus, Phase 1, "
                              "located in Navi Mumbai, India. All electrical work shall comply with the "
                              "requirements of this section and the applicable individual equipment sections."),
                            p(f"{S} Part 1.1.1.B",
                              "Related specification sections include but are not limited to: Section 26 33 53 "
                              "Static Uninterruptible Power Supply, Section 26 32 13 Engine Generators, "
                              "Section 26 13 26 Medium Voltage Switchgear, Section 23 81 23 Computer Room Air "
                              "Handling Units, and Section 21 22 00 Clean Agent Fire Suppression Systems."),
                        ],
                    },
                    {
                        "number": "1.2",
                        "title": "References",
                        "paragraphs": [
                            p(f"{S} Part 1.2.1.A",
                              "The following Indian and International standards form part of this "
                              "specification to the extent referenced herein: IS 732 (Code of Practice for "
                              "Electrical Wiring Installations), IS 3043 (Code of Practice for Earthing), "
                              "IS 694 (PVC Insulated Cables), IEC 60364 (Low Voltage Electrical Installations), "
                              "IEC 61439 (Low-Voltage Switchgear and Controlgear Assemblies)."),
                            p(f"{S} Part 1.2.1.B",
                              "All electrical installations shall comply with the National Electrical Code "
                              "(NEC) of India, the National Building Code (NBC) of India Part 8 Building "
                              "Services Section 2 Electrical and Allied Installations, and the local "
                              "regulations of the Maharashtra State Electricity Distribution Company (MSEDCL)."),
                        ],
                    },
                    {
                        "number": "1.3",
                        "title": "Submittal Requirements",
                        "paragraphs": [
                            p(f"{S} Part 1.3.1.A",
                              "The Contractor shall submit equipment shop drawings, product data sheets, "
                              "and compliance statements for each electrical equipment item specified in the "
                              "individual equipment sections. Submittals shall be transmitted using the "
                              "project standard transmittal form with a unique submittal identification number."),
                            p(f"{S} Part 1.3.1.B",
                              "Each equipment submittal shall include manufacturer's published product data, "
                              "certified performance test reports, dimensional drawings, wiring diagrams, "
                              "and a clause-by-clause compliance matrix referencing the applicable spec section."),
                            p(f"{S} Part 1.3.1.C",
                              "Submittal review turnaround time is 14 calendar days from receipt of the "
                              "complete package. Incomplete submittals will be returned without review."),
                        ],
                    },
                    {
                        "number": "1.4",
                        "title": "Quality Assurance",
                        "paragraphs": [
                            p(f"{S} Part 1.4.1.A",
                              "Equipment manufacturers shall have a minimum of 10 years demonstrated "
                              "experience in the design and manufacture of the specified equipment type, "
                              "with verifiable installations in mission-critical data centre facilities."),
                            p(f"{S} Part 1.4.1.B",
                              "Equipment manufacturers shall hold current ISO 9001 quality management "
                              "system certification from an accredited certification body for all "
                              "manufacturing facilities producing equipment for this project."),
                            p(f"{S} Part 1.4.2.A",
                              "The installing contractor shall be licensed by the appropriate state "
                              "regulatory authority and shall have a minimum of 5 years experience in "
                              "installing similar equipment in mission-critical or Tier III and above "
                              "data centre environments."),
                            # DEF-003 anchor: IEC test certificates mandate
                            p(f"{S} Part 1.4.3.A",
                              "All factory-assembled electrical equipment shall be subjected to routine "
                              "tests at the manufacturer's facility prior to shipment. Factory test "
                              "certificates shall be submitted as part of the equipment submittal package."),
                            p(f"{S} Part 1.4.3.B",
                              "All medium voltage equipment and switchgear assemblies shall be type tested "
                              "and certified in accordance with the applicable IEC standards. IEC type test "
                              "certificates from an accredited third-party laboratory (ASTA, KEMA, or "
                              "equivalent NABL-accredited body) shall be provided for each equipment type.",
                              cross_references=["26 13 26 Part 1.4.2", "26 33 53 Part 1.4.1.C"]),
                            p(f"{S} Part 1.4.3.C",
                              "Low voltage switchgear and controlgear assemblies shall be type tested "
                              "in accordance with IEC 61439-1 and IEC 61439-2. Design verification reports "
                              "shall be submitted for Consultant review."),
                            p(f"{S} Part 1.4.3.D",
                              "Power cables rated above 1.1 kV shall be type tested to IS 7098 Part 2 or "
                              "IEC 60502-2 as applicable. Cable test certificates shall include conductor "
                              "resistance, insulation resistance, and high voltage withstand test results."),
                            p(f"{S} Part 1.4.3.E",
                              "Current transformers and voltage transformers shall be type tested in "
                              "accordance with IEC 61869-2 and IEC 61869-3 respectively. Accuracy class "
                              "certificates shall be submitted."),
                            p(f"{S} Part 1.4.3.F",
                              "Protective relays and metering equipment shall be factory-calibrated and "
                              "supplied with calibration certificates traceable to national standards. "
                              "Relay settings shall be submitted for Consultant approval prior to dispatch."),
                            p(f"{S} Part 1.4.3.G",
                              "Earthing and lightning protection system components shall comply with "
                              "IS 3043 and IEC 62305. Material test certificates for copper earthing "
                              "conductors and earth electrodes shall be submitted."),
                            p(f"{S} Part 1.4.3.H",
                              "Emergency lighting and exit signs shall be tested to IS 10118 and "
                              "IS 6665. Battery backup duration and illumination level test reports "
                              "shall be submitted."),
                            p(f"{S} Part 1.4.3.I",
                              "Fire detection and alarm system components shall be tested and listed to "
                              "IS 2189 or UL 268 / UL 864 as applicable. Third-party listing certificates "
                              "shall be submitted."),
                            p(f"{S} Part 1.4.3.J",
                              "Diesel generator auxiliary systems including fuel transfer pumps, day tank "
                              "level controls, and exhaust treatment systems shall be factory tested per "
                              "the applicable IS or IEC standards. Test records shall be submitted."),
                        ],
                    },
                    {
                        "number": "1.5",
                        "title": "Warranty",
                        "paragraphs": [
                            p(f"{S} Part 1.5.1.A",
                              "The Contractor shall provide a minimum warranty period of 24 months from "
                              "the date of substantial completion or 30 months from the date of delivery, "
                              "whichever occurs first, for all electrical equipment and installations."),
                        ],
                    },
                ],
            },
            {
                "part": 2,
                "title": "PRODUCTS",
                "articles": [
                    {
                        "number": "2.1",
                        "title": "General Electrical Requirements",
                        "paragraphs": [
                            p(f"{S} Part 2.1.1.A",
                              "The campus electrical distribution system shall be designed for a nominal "
                              "medium voltage of 11 kV, 3-phase, 50 Hz from the utility incoming feed "
                              "and standby generator plant. Secondary distribution shall be at 415 V, "
                              "3-phase, 4-wire plus ground, 50 Hz."),
                            p(f"{S} Part 2.1.1.B",
                              "Power factor at the point of common coupling shall be maintained at a "
                              "minimum of 0.95 lagging. Automatic power factor correction equipment "
                              "shall be provided where required."),
                        ],
                    },
                ],
            },
            {
                "part": 3,
                "title": "EXECUTION",
                "articles": [
                    {
                        "number": "3.1",
                        "title": "Examination and Preparation",
                        "paragraphs": [
                            p(f"{S} Part 3.1.1.A",
                              "Prior to installation, the Contractor shall examine all areas and conditions "
                              "under which electrical equipment is to be installed and notify the Consultant "
                              "in writing of any conditions that may adversely affect the installation."),
                        ],
                    },
                    {
                        "number": "3.2",
                        "title": "Installation",
                        "paragraphs": [
                            p(f"{S} Part 3.2.1.A",
                              "All electrical equipment shall be installed in strict accordance with the "
                              "manufacturer's written installation instructions, approved shop drawings, "
                              "and the requirements of this specification."),
                        ],
                    },
                ],
            },
        ],
    }


def build_26_33_53():
    """Section 26 33 53 - Static Uninterruptible Power Supply."""
    S = "26 33 53"
    return {
        "title": "Static Uninterruptible Power Supply",
        "parts": [
            {
                "part": 1,
                "title": "GENERAL",
                "articles": [
                    {
                        "number": "1.1",
                        "title": "Summary",
                        "paragraphs": [
                            p(f"{S} Part 1.1.1.A",
                              "This section specifies the requirements for modular static uninterruptible "
                              "power supply (UPS) systems, battery energy storage cabinets, and associated "
                              "accessories for the Meridian Data Centre Campus, Phase 1. The UPS systems shall "
                              "provide continuous, conditioned power to the IT server load across four "
                              "independent Server Halls."),
                            p(f"{S} Part 1.1.1.B",
                              "The scope of supply includes UPS power modules, static bypass switches, "
                              "battery cabinets, monitoring and control interfaces, and all interconnecting "
                              "power and control cabling within the UPS room."),
                        ],
                    },
                    {
                        "number": "1.2",
                        "title": "References",
                        "paragraphs": [
                            p(f"{S} Part 1.2.1.A",
                              "The following standards shall apply: IEC 62040-1 (General and Safety "
                              "Requirements), IEC 62040-2 (Electromagnetic Compatibility), IEC 62040-3 "
                              "(Performance Requirements and Test Methods), IS 16242 (UPS Requirements), "
                              "IEC 60896 (Stationary Lead-Acid Batteries)."),
                        ],
                    },
                    {
                        "number": "1.3",
                        "title": "Submittal Requirements",
                        "paragraphs": [
                            # REQUIRED: DEV-UPS-R0-REV and COMP-UPS-R1-REV reference this
                            p(f"{S} Part 1.3.1",
                              "The Contractor shall submit the equipment submittal package referencing the "
                              "current active project specification revision. The active specification revision "
                              "for this section is Rev 2024. Submittals referencing an incorrect or outdated "
                              "specification revision shall be returned without review."),
                            p(f"{S} Part 1.3.2.A",
                              "Submittals shall include certified manufacturer product data sheets, "
                              "performance test reports, dimensional drawings with weights, single line "
                              "diagrams, battery sizing calculations, and a clause-by-clause compliance "
                              "matrix."),
                        ],
                    },
                    {
                        "number": "1.4",
                        "title": "Quality Assurance",
                        "paragraphs": [
                            p(f"{S} Part 1.4.1.A",
                              "UPS manufacturer shall have a minimum of 15 years experience in the design "
                              "and manufacture of static UPS systems rated above 500 kW, with at least 5 "
                              "reference installations in Tier III or above data centres."),
                            p(f"{S} Part 1.4.1.B",
                              "Manufacturing facility shall hold current ISO 9001 and ISO 14001 "
                              "certifications."),
                            # REQUIRED: DEV-UPS-R0-CERT, COMP-UPS-R1-CERT
                            p(f"{S} Part 1.4.1.C",
                              "UPS equipment shall be tested and certified in accordance with IEC 62040-3 "
                              "(Method of Specifying the Performance and Test Requirements). The Contractor "
                              "shall submit IEC 62040-3 type test reports from an accredited testing "
                              "laboratory as part of the submittal package.",
                              cross_references=["26 05 00 Part 1.4.3.B"]),
                        ],
                    },
                    {
                        "number": "1.5",
                        "title": "Warranty and Spares",
                        "paragraphs": [
                            p(f"{S} Part 1.5.1.A",
                              "The UPS manufacturer shall provide a minimum of 24 months on-site warranty "
                              "from the date of commissioning. Warranty shall include all power electronic "
                              "components, control boards, fans, and capacitors."),
                            p(f"{S} Part 1.5.1.B",
                              "A recommended spare parts list with pricing shall be submitted for Consultant "
                              "review. Minimum spares to be supplied include one complete set of control "
                              "boards, one fan assembly, and one set of DC fuses per UPS group."),
                        ],
                    },
                ],
            },
            {
                "part": 2,
                "title": "PRODUCTS",
                "articles": [
                    {
                        "number": "2.1",
                        "title": "Acceptable Manufacturers and System Configuration",
                        "paragraphs": [
                            p(f"{S} Part 2.1.1.A",
                              "Acceptable UPS manufacturers: VoltEdge Power Systems, or approved equivalent "
                              "meeting all performance requirements of this section."),
                            # DEF-001: N+2 instead of N+1 (contradicts DBR)
                            p(f"{S} Part 2.1.2.A",
                              "UPS system modules shall be configured in a minimum N+2 parallel redundant "
                              "configuration to ensure system availability during concurrent maintenance "
                              "and single fault conditions. Each Server Hall shall be served by an independent "
                              "UPS group."),
                        ],
                    },
                    {
                        "number": "2.2",
                        "title": "Performance and Design Criteria",
                        "paragraphs": [
                            # REQUIRED: COMP-UPS-R0-CAP, COMP-UPS-R1-CAP
                            p(f"{S} Part 2.2.1.A",
                              "Each UPS module shall have a minimum continuous output power rating of "
                              "1200 kW at unity power factor (1.0 PF), 415 VAC three-phase output, 50 Hz. "
                              "Rating shall be verified at 40°C ambient temperature."),
                            # REQUIRED: COMP-UPS-R0-PF, COMP-UPS-R1-PF
                            p(f"{S} Part 2.2.1.B",
                              "UPS module output power factor shall be unity (1.0 PF) at full rated load. "
                              "No derating for power factor below unity is permitted."),
                            p(f"{S} Part 2.2.1.C",
                              "UPS operating topology shall be double-conversion online mode (VFI-SS-111) "
                              "per IEC 62040-3 classification. The UPS shall provide continuous voltage and "
                              "frequency regulation independent of utility supply conditions."),
                            # REQUIRED: COMP-UPS-R0-THD, DEV-UPS-R1-THD
                            p(f"{S} Part 2.2.1.D",
                              "Input total harmonic current distortion (THDi) shall not exceed 5.0% at full "
                              "rated load without external input harmonic filters. THDi measurement shall be "
                              "per IEC 62040-3 Annex E."),
                            # REQUIRED: COMP-UPS-R0-EFF100
                            p(f"{S} Part 2.2.2.A",
                              "Double-conversion online mode efficiency at 100% rated load shall be a "
                              "minimum of 96.0%. Efficiency shall be measured per IEC 62040-3 at nominal "
                              "input voltage and rated load."),
                            # REQUIRED: DEV-UPS-R0-EFF50, COMP-UPS-R0-EFF75
                            p(f"{S} Part 2.2.2.B",
                              "Double-conversion online mode efficiency at 75% and 50% rated load shall "
                              "each be a minimum of 96.0%. All efficiency values shall be measured in VFI "
                              "mode with harmonic filters active."),
                            p(f"{S} Part 2.2.3.A",
                              "Output voltage regulation shall be within +/- 1% of nominal under steady "
                              "state conditions, and within +/- 5% during 100% load step transients, "
                              "with recovery to +/- 1% within 20 milliseconds."),
                            p(f"{S} Part 2.2.4.A",
                              "Output frequency regulation shall be within +/- 0.1% of 50 Hz under "
                              "free-running conditions."),
                            # REQUIRED: DEV-UPS-R0-OVERLOAD, DEV-UPS-R1-OVERLOAD
                            p(f"{S} Part 2.2.5.A",
                              "UPS module shall sustain 125% of rated load for a minimum of 10 minutes "
                              "continuously without transfer to static bypass. At 150% overload, the UPS "
                              "shall sustain the load for a minimum of 30 seconds before bypass transfer."),
                            p(f"{S} Part 2.2.6.A",
                              "Input power factor shall be 0.99 or better at full rated load."),
                            p(f"{S} Part 2.2.7.A",
                              "ECO mode efficiency shall be a minimum of 99.0% at rated load. ECO mode "
                              "transfer to double-conversion mode shall occur within 2 milliseconds of "
                              "detecting input power disturbance."),
                            # REQUIRED: DEV-UPS-R0-MISS-PARAM, DEV-UPS-R1-MISS-PARAM
                            p(f"{S} Part 2.2.8",
                              "The static bypass switch transfer time shall not exceed 4 milliseconds for "
                              "any transfer between inverter output and bypass supply, measured as total "
                              "interruption duration per IEC 62040-3 classification."),
                        ],
                    },
                    {
                        "number": "2.3",
                        "title": "Battery and Energy Storage System",
                        "paragraphs": [
                            p(f"{S} Part 2.3.1.A",
                              "Battery system shall use Valve Regulated Lead-Acid (VRLA) batteries in "
                              "sealed maintenance-free construction mounted in dedicated battery cabinets."),
                            p(f"{S} Part 2.3.1.B",
                              "Battery system shall comprise 240 cells of 2 V nominal (40 blocks of "
                              "12 V batteries in series) providing a nominal DC bus voltage of 480 VDC."),
                            p(f"{S} Part 2.3.1.C",
                              "Battery string configuration shall consist of a minimum of 6 parallel "
                              "strings of 200 Ah (C10 rate) battery blocks per UPS module."),
                            p(f"{S} Part 2.3.1.D",
                              "Battery monitoring system shall include individual block voltage monitoring, "
                              "string current monitoring, ambient and pilot cell temperature sensors, and "
                              "Modbus TCP/IP interface for integration with the BMS."),
                            # DEF-002 part 1: says 10.0 minutes (contradicts Part 3.4.2.C which says 12)
                            p(f"{S} Part 2.3.1.E",
                              "The battery system shall support the full rated UPS load at 100% capacity "
                              "for a minimum continuous runtime of 10.0 minutes. Battery sizing calculations "
                              "shall account for the high-rate discharge factor and end-of-life capacity "
                              "degradation of 20%."),
                            # REQUIRED: DEV-BAT-UNIT-SHORTFALL, DEV-BAT-UNIT-KWH
                            p(f"{S} Part 2.3.2.A",
                              "Total battery bank nominal energy capacity shall be a minimum of 576 kWh "
                              "at the nominal DC bus voltage of 480 VDC, equivalent to a minimum of "
                              "1200 Ah at the C10 rate. Vendor datasheet shall clearly state both kWh and "
                              "Ah capacity values."),
                            # REQUIRED: DEV-BAT-COND-PF
                            p(f"{S} Part 2.3.2.B",
                              "Battery runtime performance shall be rated and verified at a load power "
                              "factor of 1.0 PF (unity). Runtime claims at reduced power factors shall not "
                              "be accepted as equivalent."),
                            # REQUIRED: DEV-BAT-DCBUS
                            p(f"{S} Part 2.3.2.C",
                              "Battery system nominal DC bus voltage shall be 480 VDC to match the UPS "
                              "inverter DC link requirements. End-of-discharge voltage shall not fall below "
                              "408 VDC (1.7 V per cell)."),
                            # REQUIRED: DEV-BAT-MISS-PARAM
                            p(f"{S} Part 2.3.3",
                              "Battery shelf life without charge shall be a minimum of 6 months from the "
                              "date of manufacture without permanent capacity loss. The vendor shall submit "
                              "storage conditions and shelf life test data as part of the submittal."),
                            # REQUIRED: Addendum 3 changes this from 96.0% to 96.5%
                            p(f"{S} Part 2.3.4",
                              "UPS double-conversion efficiency shall be a minimum of 96.0% at each of the "
                              "50%, 75%, and 100% load points, measured in VFI mode per IEC 62040-3. "
                              "Efficiency values shall be based on active power (kW) measurements."),
                            # REQUIRED: DEV-BAT-CABINET-WEIGHT
                            p(f"{S} Part 2.3.5.A",
                              "Maximum floor-load weight per fully loaded battery cabinet shall not exceed "
                              "2800 kg. Floor loading calculations based on cabinet footprint and weight "
                              "distribution shall be submitted for structural review."),
                            p(f"{S} Part 2.3.5.B",
                              "Battery cabinet dimensions shall permit standard freight elevator transport. "
                              "Maximum individual module shipping weight shall be noted on the dimensional "
                              "drawing."),
                            p(f"{S} Part 2.3.6.A",
                              "Battery design life shall be a minimum of 10 years at 25°C average ambient "
                              "temperature per IEC 60896-21 / Eurobat classification."),
                            # REQUIRED: DEV-BAT-OPERATING-TEMP
                            p(f"{S} Part 2.3.6.B",
                              "Battery system shall maintain full manufacturer warranty coverage and "
                              "published performance parameters across an ambient operating temperature "
                              "range of 0°C to 25°C."),
                            p(f"{S} Part 2.3.7.A",
                              "Battery cabinets shall include hydrogen gas detection sensors with alarm "
                              "contacts connected to the BMS. Ventilation calculations for the battery "
                              "room shall be submitted per IEC 62485-2."),
                            # REQUIRED: DEV-BAT-CABLE-ENTRY
                            p(f"{S} Part 2.3.8",
                              "Battery cabinet power cable entry shall accommodate both top and bottom "
                              "cable entry conduits to match overhead cable tray or under-floor cable "
                              "routing as determined by the final installation layout."),
                            p(f"{S} Part 2.3.9.A",
                              "Each battery cabinet shall incorporate a manual maintenance bypass switch "
                              "allowing isolation of individual battery strings without disrupting the "
                              "remaining parallel strings."),
                            p(f"{S} Part 2.3.9.B",
                              "Battery cabinet DC distribution shall include appropriately rated fuses "
                              "or circuit breakers on each battery string for short circuit protection."),
                            # REQUIRED: DEV-BAT-LVD-VALVE
                            p(f"{S} Part 2.3.9.C",
                              "A Low Voltage Disconnect (LVD) contactor shall be provided on each battery "
                              "cabinet to prevent deep discharge damage. The LVD contactor ampere rating "
                              "and breaking capacity shall be submitted with the battery cabinet "
                              "specification sheet."),
                        ],
                    },
                    {
                        "number": "2.4",
                        "title": "Physical Construction and Enclosure",
                        "paragraphs": [
                            p(f"{S} Part 2.4.1.A",
                              "UPS module enclosure shall be constructed of minimum 1.6 mm steel sheet "
                              "with IP20 minimum ingress protection rating per IEC 60529."),
                            p(f"{S} Part 2.4.1.B",
                              "Enclosure shall include lockable front and rear access doors with "
                              "captive fasteners. Minimum service clearance of 1000 mm shall be "
                              "maintained on all accessible sides."),
                            # REQUIRED: DEV-UPS-R0-AIRFLOW-PATH, DEV-UPS-R1-AIRFLOW-PATH
                            p(f"{S} Part 2.4.2",
                              "UPS module cooling airflow shall be configured for front-inlet and "
                              "top-exhaust to support hot aisle/cold aisle containment architecture in the "
                              "UPS room. Rear-exhaust or side-exhaust configurations are not acceptable."),
                            p(f"{S} Part 2.4.3.A",
                              "UPS module cooling fans shall be hot-swappable without requiring UPS "
                              "shutdown or load transfer. Fan failure alarms shall be reported via the "
                              "monitoring interface."),
                            p(f"{S} Part 2.4.4.A",
                              "All internal power connections shall utilise bolted joints with calibrated "
                              "torque values marked on the assembly. Spring-type terminal connections are "
                              "not permitted for power circuits above 100 A."),
                            p(f"{S} Part 2.4.5.A",
                              "UPS module enclosure shall have a seismic rating suitable for Zone III per "
                              "IS 1893 or equivalent IBC classification."),
                            p(f"{S} Part 2.4.5.B",
                              "Equipment shall be suitable for installation on a raised access floor "
                              "with standard pedestal height of 600 mm. Anti-vibration pads shall be "
                              "provided under all mounting points."),
                            # REQUIRED: DEV-UPS-R0-PAINT, DEV-UPS-R1-PAINT
                            p(f"{S} Part 2.4.5.C",
                              "UPS module enclosure paint finish shall be RAL 7035 (Light Grey) polyester "
                              "powder coating, minimum 60 micron average dry film thickness, with "
                              "corrosion resistance suitable for indoor C1 environment per ISO 12944."),
                        ],
                    },
                ],
            },
            {
                "part": 3,
                "title": "EXECUTION",
                "articles": [
                    {
                        "number": "3.1",
                        "title": "Examination and Preparation",
                        "paragraphs": [
                            p(f"{S} Part 3.1.1.A",
                              "Prior to delivery, the Contractor shall verify that the UPS room "
                              "structural slab, cable trays, and HVAC provisions are complete and "
                              "ready to receive equipment."),
                        ],
                    },
                    {
                        "number": "3.2",
                        "title": "Installation",
                        "paragraphs": [
                            # REQUIRED: CX-TEST-L2-01 through L2-05
                            p(f"{S} Part 3.2.1",
                              "Verify all power cable terminations have been torque-marked per "
                              "manufacturer specifications. Inspect structural mounting bolts and "
                              "anti-vibration pads for Module 1. Record torque values on the "
                              "commissioning checklist."),
                            p(f"{S} Part 3.2.2",
                              "Verify all power cable terminations have been torque-marked per "
                              "manufacturer specifications. Inspect structural mounting bolts and "
                              "anti-vibration pads for Module 2. Record torque values on the "
                              "commissioning checklist."),
                            p(f"{S} Part 3.2.3",
                              "Verify all power cable terminations have been torque-marked per "
                              "manufacturer specifications. Inspect structural mounting bolts and "
                              "anti-vibration pads for Module 3. Record torque values on the "
                              "commissioning checklist."),
                            p(f"{S} Part 3.2.4",
                              "Verify all power cable terminations have been torque-marked per "
                              "manufacturer specifications. Inspect structural mounting bolts and "
                              "anti-vibration pads for Module 4. Record torque values on the "
                              "commissioning checklist."),
                            p(f"{S} Part 3.2.5",
                              "Verify all power cable terminations have been torque-marked per "
                              "manufacturer specifications. Inspect structural mounting bolts and "
                              "anti-vibration pads for Module 5. Record torque values on the "
                              "commissioning checklist."),
                        ],
                    },
                    {
                        "number": "3.3",
                        "title": "Field Quality Control",
                        "paragraphs": [
                            p(f"{S} Part 3.3.1.A",
                              "Perform insulation resistance testing on all power cables prior to "
                              "energisation. Minimum acceptable insulation resistance is 100 MΩ at "
                              "1000 VDC for LV circuits."),
                        ],
                    },
                    {
                        "number": "3.4",
                        "title": "Commissioning and Acceptance Testing",
                        "paragraphs": [
                            p(f"{S} Part 3.4.1.A",
                              "The commissioning agent shall perform a complete functional test of each "
                              "UPS module including input/output voltage verification, frequency stability, "
                              "and battery charger operation."),
                            # REQUIRED: CX-UPS-L5-01
                            p(f"{S} Part 3.4.2.A",
                              "Verify UPS double-conversion efficiency is a minimum of 96.0% at both 100% "
                              "and 75% rated load points. Efficiency measurements shall use calibrated "
                              "power analysers with accuracy class 0.5 or better."),
                            p(f"{S} Part 3.4.2.B",
                              "Perform input harmonic current measurement at full rated load. Input THDi "
                              "shall not exceed the value specified in Part 2.2.1.D of this section."),
                            # DEF-002 part 2: says 12 minutes (contradicts Part 2.3.1.E which says 10)
                            # REQUIRED: CX-UPS-L5-02, CX-TEST-L5-03
                            p(f"{S} Part 3.4.2.C",
                              "During site battery discharge testing, the inverter shall maintain full 100% "
                              "IT load for a minimum of 12 minutes on battery power. The discharge test "
                              "shall be conducted at design ambient temperature with all battery strings "
                              "connected."),
                            # REQUIRED: CX-TEST-L5-04 through L5-10
                            p(f"{S} Part 3.4.2.D",
                              "Perform UPS static bypass transfer test. Verify seamless transfer from "
                              "inverter to bypass and back with no load interruption exceeding the "
                              "specified transfer time."),
                            p(f"{S} Part 3.4.2.E",
                              "Verify UPS module parallel operation and active load sharing. Load "
                              "imbalance between parallel modules shall not exceed 5% of rated load."),
                            p(f"{S} Part 3.4.2.F",
                              "Simulate single module failure and verify N+1 redundancy takeover. "
                              "Remaining modules shall assume full load without interruption."),
                            p(f"{S} Part 3.4.2.G",
                              "Perform 100% load step test and verify output voltage transient recovery "
                              "is within the limits specified in Part 2.2.3.A of this section."),
                            p(f"{S} Part 3.4.2.H",
                              "Verify battery recharge time from fully discharged state. Battery system "
                              "shall reach 90% of nominal capacity within 8 hours of recharge initiation."),
                            p(f"{S} Part 3.4.2.I",
                              "Perform BMS communication integration test. Verify all UPS alarm and status "
                              "signals are correctly mapped and displayed on the central BMS operator "
                              "console."),
                            p(f"{S} Part 3.4.2.J",
                              "Execute a coordinated full-load transfer test from utility to generator and "
                              "back. Verify the UPS maintains uninterrupted output power throughout the "
                              "transfer sequence."),
                        ],
                    },
                ],
            },
        ],
    }


def build_26_32_13():
    """Section 26 32 13 - Engine Generators."""
    S = "26 32 13"
    return {
        "title": "Engine Generators",
        "parts": [
            {
                "part": 1,
                "title": "GENERAL",
                "articles": [
                    {
                        "number": "1.1",
                        "title": "Summary",
                        "paragraphs": [
                            p(f"{S} Part 1.1.1.A",
                              "This section specifies the requirements for standby diesel engine generator "
                              "sets for the Meridian Data Centre Campus, Phase 1. The generator plant shall "
                              "provide emergency power to the full campus load including IT systems, cooling, "
                              "and building services during utility power interruptions."),
                        ],
                    },
                    {
                        "number": "1.2",
                        "title": "References",
                        "paragraphs": [
                            p(f"{S} Part 1.2.1.A",
                              "The following standards shall apply: ISO 8528 (Reciprocating Internal "
                              "Combustion Engine Driven Alternating Current Generating Sets), IS 10000 "
                              "(Methods of Tests for IC Engines), IS 13364 (Gas/Dual Fuel Engine Generator "
                              "Sets), BS 5514 (Reciprocating IC Engines Performance), NFPA 110 (Standard "
                              "for Emergency and Standby Power Systems)."),
                        ],
                    },
                    {
                        "number": "1.3",
                        "title": "Submittal Requirements",
                        "paragraphs": [
                            p(f"{S} Part 1.3.1.A",
                              "Submittals shall include engine performance data sheets, alternator test "
                              "certificates, fuel consumption curves at 25%, 50%, 75%, and 100% load, "
                              "ambient derating curves, noise emission data, exhaust emission data, "
                              "and dimensional drawings with weights."),
                        ],
                    },
                    {
                        "number": "1.4",
                        "title": "Quality Assurance",
                        "paragraphs": [
                            p(f"{S} Part 1.4.1.A",
                              "Generator set manufacturer shall have ISO 9001 certification and a minimum "
                              "of 10 years experience in manufacturing standby generator sets rated above "
                              "1500 kVA for mission-critical installations.",
                              cross_references=["26 05 00 Part 1.4.3.B"]),
                        ],
                    },
                    {
                        "number": "1.5",
                        "title": "Warranty",
                        "paragraphs": [
                            p(f"{S} Part 1.5.1.A",
                              "Generator set warranty shall be a minimum of 24 months from the date of "
                              "commissioning or 2000 operating hours, whichever occurs first. Warranty "
                              "shall cover engine, alternator, control system, and all factory-supplied "
                              "accessories."),
                        ],
                    },
                ],
            },
            {
                "part": 2,
                "title": "PRODUCTS",
                "articles": [
                    {
                        "number": "2.1",
                        "title": "Acceptable Manufacturers",
                        "paragraphs": [
                            p(f"{S} Part 2.1.1.A",
                              "Acceptable generator set manufacturers: Deccan Diesel Co., or approved "
                              "equivalent meeting all performance requirements of this section."),
                        ],
                    },
                    {
                        "number": "2.2",
                        "title": "Performance and Design Criteria",
                        "paragraphs": [
                            # REQUIRED: DEV-GEN-TEMP
                            p(f"{S} Part 2.2.1.A",
                              "Generator standby power rating shall be a minimum of 2500 kVA. The standby "
                              "rating shall be verified and guaranteed at the project design basis ambient "
                              "temperature of 45°C. Ratings quoted at lower reference ambient temperatures "
                              "shall be derated per the manufacturer's published derating curve."),
                            # REQUIRED: DEV-GEN-SHORTFALL
                            p(f"{S} Part 2.2.1.B",
                              "After applying the manufacturer's published ambient temperature derating "
                              "factors for operation at 45°C, the available standby output shall not fall "
                              "below 2500 kVA. The vendor shall submit the derating curve and demonstrate "
                              "compliance at design ambient."),
                            # REQUIRED: COMP-GEN-PF
                            p(f"{S} Part 2.2.1.C",
                              "Generator power factor rating shall be 0.8 lagging. Generator shall be "
                              "capable of delivering rated kW output continuously at 0.8 power factor."),
                            # REQUIRED: COMP-GEN-VOLT
                            p(f"{S} Part 2.2.1.D",
                              "Generator output voltage shall be 11 kV, 3-phase, 50 Hz. Voltage "
                              "regulation shall be within +/- 0.5% under steady-state conditions."),
                            # REQUIRED: COMP-GEN-SPEED
                            p(f"{S} Part 2.2.1.E",
                              "Generator operating speed shall be 1500 RPM synchronous for 50 Hz output. "
                              "Speed governing shall meet ISO 8528-5 performance class G3 requirements."),
                            # REQUIRED: COMP-GEN-LOAD
                            p(f"{S} Part 2.2.2",
                              "Generator shall accept 100% block load in a single step and recover to "
                              "steady-state voltage and frequency within the limits specified by ISO 8528-5 "
                              "performance class G3. Transient voltage dip shall not exceed 15% and "
                              "recovery to within 3% shall occur within 10 seconds."),
                            p(f"{S} Part 2.2.3.A",
                              "Fuel consumption rate at 100% standby load shall not exceed 520 litres per "
                              "hour of high speed diesel (HSD) conforming to IS 1460. The vendor shall "
                              "submit a fuel consumption certificate from the engine manufacturer."),
                            p(f"{S} Part 2.2.4.A",
                              "Fuel consumption rate at 75% load shall be submitted in the vendor "
                              "performance data table."),
                            p(f"{S} Part 2.2.4.B",
                              "Fuel consumption rate at 25% load shall be submitted in the vendor "
                              "performance data table."),
                            p(f"{S} Part 2.2.4.C",
                              "The vendor shall submit a complete performance data table listing engine "
                              "output power, alternator output, fuel consumption, exhaust temperature, "
                              "and cooling water temperature at 25%, 50%, 75%, and 100% load points."),
                            # REQUIRED: DEV-GEN-MISS-PARAM
                            p(f"{S} Part 2.2.4.D",
                              "Fuel consumption rate at 50% load shall be submitted in the vendor "
                              "performance data table. Omission of any load point data from the "
                              "performance table shall be treated as a non-compliant submittal."),
                        ],
                    },
                    {
                        "number": "2.3",
                        "title": "Component Description",
                        "paragraphs": [
                            p(f"{S} Part 2.3.1.A",
                              "Engine shall be a multi-cylinder, turbocharged, charge air-cooled, "
                              "4-stroke diesel engine designed for standby duty. Engine shall conform "
                              "to CPCB Stage IV emission norms or equivalent."),
                            # REQUIRED: COMP-GEN-GOVERNOR
                            p(f"{S} Part 2.3.2.A",
                              "Engine speed governor shall be electronic type, meeting ISO 8528-5 "
                              "performance class G3 requirements. Governor shall provide isochronous "
                              "frequency control suitable for paralleling applications."),
                            # REQUIRED: DEV-GEN-STARTER
                            p(f"{S} Part 2.3.3.A",
                              "Generator shall be equipped with dual starter motors in redundant "
                              "configuration, each with independent 24 VDC starter batteries and battery "
                              "chargers. Automatic crank sequence shall attempt start on the primary "
                              "starter, and transfer to the secondary starter after three failed attempts."),
                            p(f"{S} Part 2.3.4.A",
                              "Alternator shall be brushless, self-excited, with a permanent magnet pilot "
                              "exciter. Insulation class shall be Class H (180°C) with Class F (155°C) "
                              "temperature rise at rated load."),
                            # REQUIRED: DEV-GEN-OBS-CERT
                            p(f"{S} Part 2.3.5.A",
                              "Generator controller shall be the current model EMCP 4.4 digital "
                              "electronic control panel, or approved equivalent, providing engine "
                              "monitoring, protection, and paralleling control functions. Obsolete "
                              "controller versions shall not be accepted."),
                            p(f"{S} Part 2.3.6.A",
                              "Radiator cooling system shall be engine-driven with belt-driven fans. "
                              "Cooling system shall be designed for continuous operation at 45°C ambient "
                              "temperature."),
                            p(f"{S} Part 2.3.7.A",
                              "Exhaust system shall include a hospital-grade residential silencer "
                              "providing a minimum of 25 dBA attenuation. Exhaust piping shall be "
                              "insulated and lagged to limit surface temperature to below 60°C."),
                            p(f"{S} Part 2.3.8.A",
                              "Bulk fuel storage system shall consist of 4 underground double-walled "
                              "steel tanks of 100,000 litres each, providing 48 hours of fuel autonomy "
                              "for the complete generator plant at full standby load."),
                            p(f"{S} Part 2.3.8.B",
                              "Fuel transfer pumping system shall include duty and standby transfer pumps "
                              "with automatic changeover. The fuel transfer system shall maintain the local "
                              "day tank level between the high and low level setpoints at all times."),
                            # DEF-007: 2.0 hours day tank (1040L) conflicts with <1000L code cap
                            p(f"{S} Part 2.3.8.C",
                              "Each generator shall be provided with a local day tank sized to provide a "
                              "minimum of 2.0 hours of continuous operation at full standby load. Based on "
                              "the specified fuel consumption rate of 520 litres per hour, the minimum "
                              "day tank capacity shall be 1040 litres."),
                        ],
                    },
                    {
                        "number": "2.4",
                        "title": "Physical Construction and Acoustic Treatment",
                        "paragraphs": [
                            p(f"{S} Part 2.4.1.A",
                              "Generator set base frame shall be heavy-duty fabricated steel with integral "
                              "anti-vibration mounts. Base frame shall include a fuel-tight drip tray."),
                            p(f"{S} Part 2.4.2.A",
                              "Generator set enclosure (if outdoor installation) shall be weatherproof "
                              "to IP44 with acoustic lining to meet the specified noise limits."),
                            p(f"{S} Part 2.4.3.A",
                              "Generator set noise level shall not exceed 105 dBA at 1 metre distance "
                              "without acoustic enclosure. Manufacturer shall state the open-set and "
                              "enclosed noise levels separately."),
                            # REQUIRED: DEV-GEN-SOUND
                            p(f"{S} Part 2.4.3.B",
                              "With the acoustic enclosure and silencer installed, the generator set "
                              "sound pressure level shall not exceed 85 dBA measured in a free field at "
                              "1 metre distance from the enclosure surface at full rated standby load."),
                        ],
                    },
                ],
            },
            {
                "part": 3,
                "title": "EXECUTION",
                "articles": [
                    {
                        "number": "3.1",
                        "title": "Examination and Preparation",
                        "paragraphs": [
                            p(f"{S} Part 3.1.1.A",
                              "Verify that generator room foundations, exhaust penetrations, fuel piping, "
                              "and electrical cable routes are complete and ready prior to generator "
                              "delivery."),
                        ],
                    },
                    {
                        "number": "3.2",
                        "title": "Installation",
                        "paragraphs": [
                            p(f"{S} Part 3.2.1.A",
                              "Generator sets shall be rigged and placed on prepared foundations using "
                              "certified lifting equipment. Anti-vibration mounts shall be adjusted to "
                              "achieve level installation within 2 mm across the base frame."),
                            p(f"{S} Part 3.2.1.B",
                              "Flexible fuel connections, exhaust bellows, and cable gland plates shall "
                              "be installed per manufacturer details. All fuel connections shall be leak "
                              "tested at 1.5 times working pressure."),
                            p(f"{S} Part 3.2.1.C",
                              "Battery banks and chargers shall be installed and commissioned prior to "
                              "engine first start. Electrolyte levels shall be verified in flooded-type "
                              "batteries."),
                            p(f"{S} Part 3.2.1.D",
                              "Cooling water system shall be filled, vented, and leak tested. Coolant "
                              "mixture shall be per engine manufacturer's recommendation for the local "
                              "climate conditions."),
                            p(f"{S} Part 3.2.1.E",
                              "All generator room cable trays, busbar trunking, and power cable "
                              "terminations shall be completed and torque-marked prior to energisation "
                              "of the generator output circuit breaker."),
                            # DEF-005: "adequate ventilation" with no quantitative requirement
                            p(f"{S} Part 3.2.1.F",
                              "Adequate ventilation shall be provided in the generator room to prevent "
                              "heat buildup and ensure proper engine combustion air supply during full "
                              "load operation. Room ventilation provisions shall be verified complete "
                              "prior to engine commissioning."),
                        ],
                    },
                    {
                        "number": "3.3",
                        "title": "Startup and Field Testing",
                        "paragraphs": [
                            p(f"{S} Part 3.3.1.A",
                              "Prior to initial start, perform a complete pre-start checklist including "
                              "oil level, coolant level, belt tension, battery voltage, and control "
                              "system self-test."),
                            p(f"{S} Part 3.3.2.A",
                              "Perform initial no-load start test. Engine shall reach rated speed and "
                              "voltage within 10 seconds of the start command."),
                            # REQUIRED: CX-TEST-L3-03 through L3-05
                            p(f"{S} Part 3.3.3",
                              "Perform initial start sequence and voltage balance checks for engine 3. "
                              "Verify three-phase voltage balance is within 1% of nominal at no load "
                              "and at 50% load."),
                            p(f"{S} Part 3.3.4",
                              "Perform initial start sequence and voltage balance checks for engine 4. "
                              "Verify three-phase voltage balance is within 1% of nominal at no load "
                              "and at 50% load."),
                            # REQUIRED: CX-GEN-L4-01
                            p(f"{S} Part 3.3.4.A",
                              "Perform 100% block load acceptance test in a single step per ISO 8528-5 "
                              "performance class G3. Record transient voltage dip, frequency dip, and "
                              "recovery times. Results shall meet the limits specified in Part 2.2.2 "
                              "of this section."),
                            p(f"{S} Part 3.3.5",
                              "Perform initial start sequence and voltage balance checks for engine 5. "
                              "Verify three-phase voltage balance is within 1% of nominal at no load "
                              "and at 50% load."),
                        ],
                    },
                ],
            },
        ],
    }


def build_26_13_26():
    """Section 26 13 26 - Medium Voltage Switchgear."""
    S = "26 13 26"
    return {
        "title": "Medium Voltage Switchgear",
        "parts": [
            {
                "part": 1,
                "title": "GENERAL",
                "articles": [
                    {
                        "number": "1.1",
                        "title": "Summary",
                        "paragraphs": [
                            p(f"{S} Part 1.1.1.A",
                              "This section specifies the requirements for factory-assembled, "
                              "metal-enclosed, medium voltage switchgear for the 11 kV power distribution "
                              "system of the Meridian Data Centre Campus, Phase 1."),
                        ],
                    },
                    {
                        "number": "1.2",
                        "title": "References",
                        "paragraphs": [
                            # DEF-003: UL-only reference, conflicts with 26 05 00 Part 1.4.3.B
                            p(f"{S} Part 1.2.1",
                              "All medium voltage switchgear assemblies shall comply with UL 1558 (Standard "
                              "for Metal-Enclosed Low-Voltage Power Circuit Breaker Switchgear) and shall be "
                              "UL listed and labeled. Switchgear components shall be UL recognized or listed "
                              "as applicable."),
                            p(f"{S} Part 1.2.2.A",
                              "Additional applicable standards include: IS 3427 (Metal-Enclosed Switchgear), "
                              "IS/IEC 62271-200 (AC Metal-Enclosed Switchgear for Rated Voltages Above 1 kV "
                              "and Up To and Including 52 kV), IEC 62271-1 (Common Specifications for "
                              "High-Voltage Switchgear)."),
                        ],
                    },
                    {
                        "number": "1.3",
                        "title": "Submittal Requirements",
                        "paragraphs": [
                            p(f"{S} Part 1.3.1.A",
                              "Submittals shall include general arrangement drawings, single line diagrams, "
                              "control schematics, busbar current rating calculations, type test reports, "
                              "and a clause-by-clause compliance matrix."),
                        ],
                    },
                    {
                        "number": "1.4",
                        "title": "Quality Assurance",
                        "paragraphs": [
                            p(f"{S} Part 1.4.1.A",
                              "Switchgear manufacturer shall have a minimum of 15 years experience in "
                              "manufacturing medium voltage switchgear assemblies rated 12 kV and above."),
                            # REQUIRED: COMP-SWG-CERT
                            p(f"{S} Part 1.4.2",
                              "Manufacturer shall provide ASTA or KEMA type test certificates for the "
                              "switchgear assemblies demonstrating compliance with IEC 62271-200. Type test "
                              "reports shall cover rated voltage, short circuit withstand, temperature rise, "
                              "internal arc, and dielectric tests.",
                              cross_references=["26 05 00 Part 1.4.3.B"]),
                            p(f"{S} Part 1.4.3.A",
                              "Manufacturing facility shall hold current ISO 9001 certification. The "
                              "Consultant reserves the right to conduct a factory inspection prior to "
                              "dispatch."),
                            p(f"{S} Part 1.4.4.A",
                              "Routine factory tests shall be conducted on each switchgear panel prior to "
                              "dispatch, including power frequency voltage withstand, mechanical operation, "
                              "and wiring checks per IEC 62271-200 Clause 8."),
                            # REQUIRED: COMP-SWG-OPER-TEMP
                            p(f"{S} Part 1.4.5",
                              "Switchgear shall be rated for continuous operation over an ambient "
                              "temperature range of -5°C to 45°C. Temperature rise of busbars and "
                              "connections shall not exceed the limits specified in IEC 62271-200 Table 4 "
                              "at 45°C ambient."),
                        ],
                    },
                ],
            },
            {
                "part": 2,
                "title": "PRODUCTS",
                "articles": [
                    {
                        "number": "2.1",
                        "title": "Acceptable Manufacturers",
                        "paragraphs": [
                            p(f"{S} Part 2.1.1.A",
                              "Acceptable switchgear manufacturers: Trident Switchgear, or approved "
                              "equivalent meeting all performance requirements of this section."),
                        ],
                    },
                    {
                        "number": "2.2",
                        "title": "Electrical Ratings",
                        "paragraphs": [
                            # REQUIRED: COMP-SWG-VOLT
                            p(f"{S} Part 2.2.1.A",
                              "Switchgear rated voltage shall be 12 kV, suitable for the 11 kV nominal "
                              "system voltage. Rated insulation level shall be 12/28/75 kV "
                              "(rated voltage / power frequency withstand / lightning impulse withstand)."),
                            # REQUIRED: COMP-SWG-AMP
                            p(f"{S} Part 2.2.1.B",
                              "Main busbar continuous current rating shall be a minimum of 2000 A at "
                              "45°C ambient temperature."),
                            # REQUIRED: COMP-SWG-KA
                            p(f"{S} Part 2.2.2.A",
                              "Rated short-time withstand current shall be a minimum of 31.5 kA (rms) "
                              "for a duration of 3 seconds."),
                            # REQUIRED: COMP-SWG-TIME
                            p(f"{S} Part 2.2.2.B",
                              "Short-circuit current withstand duration shall be a minimum of 3 seconds. "
                              "All busbars, connections, and supporting insulators shall be rated "
                              "accordingly."),
                            # REQUIRED: COMP-SWG-MAKING
                            p(f"{S} Part 2.2.3",
                              "Rated short-circuit making capacity shall be a minimum of 66 kA peak. "
                              "Circuit breakers shall have a making capacity not less than the peak "
                              "value of the rated short-circuit withstand current."),
                            # REQUIRED: COMP-SWG-BIL
                            p(f"{S} Part 2.2.4",
                              "Rated lightning impulse withstand voltage (BIL) shall be a minimum of "
                              "75 kV (1.2/50 microsecond wave). Power frequency withstand voltage shall "
                              "be 28 kV for 1 minute."),
                        ],
                    },
                    {
                        "number": "2.3",
                        "title": "Construction and Components",
                        "paragraphs": [
                            # REQUIRED: COMP-SWG-IP
                            p(f"{S} Part 2.3.1.A",
                              "Switchgear enclosure external protection shall be a minimum of IP4X per "
                              "IEC 60529. Internal compartment protection between functional units shall "
                              "be IP2X minimum."),
                            p(f"{S} Part 2.3.1.B",
                              "Switchgear construction shall be compartmentalised type with metallic "
                              "shutters on all circuit breaker compartments, busbar compartments, and "
                              "cable compartments."),
                            p(f"{S} Part 2.3.1.C",
                              "Circuit breakers shall be vacuum type, withdrawable on truck mechanism. "
                              "Breaker truck shall have test, connected, and disconnected positions with "
                              "mechanical interlocks."),
                            p(f"{S} Part 2.3.1.D",
                              "Anti-condensation space heaters shall be provided in each switchgear "
                              "compartment. Heaters shall be thermostatically controlled and powered "
                              "from the auxiliary supply."),
                            # REQUIRED: COMP-SWG-IAC
                            p(f"{S} Part 2.3.1.E",
                              "Switchgear shall be classified for Internal Arc Containment (IAC) AFLR "
                              "(Accessibility: Front, Lateral, Rear) rated for 31.5 kA for 1 second per "
                              "IEC 62271-200 Annex A."),
                            # REQUIRED: COMP-SWG-LSC
                            p(f"{S} Part 2.3.1.F",
                              "Loss of service continuity classification shall be LSC-2B per "
                              "IEC 62271-200, ensuring that maintenance on any single functional unit "
                              "does not require de-energisation of adjacent units."),
                            # REQUIRED: COMP-SWG-BUS-MAT
                            p(f"{S} Part 2.3.2.A",
                              "Main busbars shall be high conductivity electrolytic copper, silver-plated "
                              "at all joint surfaces. Busbars shall be sized for the rated continuous "
                              "current with temperature rise within IEC 62271-200 limits."),
                            p(f"{S} Part 2.3.3.A",
                              "Cable termination compartment shall accommodate XLPE-insulated cables "
                              "with heat-shrink terminations. Cable compartment depth shall be a minimum "
                              "of 600 mm."),
                            # REQUIRED: COMP-SWG-EARTH
                            p(f"{S} Part 2.3.3.B",
                              "Earthing busbar shall be high conductivity copper, continuous throughout "
                              "the switchgear lineup, and sized for the full rated short circuit current. "
                              "Earth bus connections shall be bolted with calibrated torque."),
                            p(f"{S} Part 2.3.4.A",
                              "Circuit breaker operating mechanism shall be spring-charged, motor-wound "
                              "type suitable for auto-reclosing. Stored energy shall be sufficient for "
                              "one close-open-close operation."),
                            p(f"{S} Part 2.3.5.A",
                              "Protection relays shall be microprocessor-based numerical type with "
                              "overcurrent, earth fault, and under/over voltage functions. Relay "
                              "communications shall be IEC 61850 compatible."),
                            p(f"{S} Part 2.3.6.A",
                              "Metering instruments shall include digital multifunction meters with "
                              "accuracy class 0.5. Meters shall display voltage, current, power, energy, "
                              "power factor, and frequency."),
                            # REQUIRED: COMP-SWG-CT-ACC
                            p(f"{S} Part 2.3.7.A",
                              "Current transformers shall have metering accuracy class 0.5s and protection "
                              "accuracy class 5P20. CT ratios shall be as shown on the single line diagram."),
                            p(f"{S} Part 2.3.7.B",
                              "Current transformers shall have a rated burden not less than the connected "
                              "metering and protection burden with a 25% margin."),
                            # REQUIRED: COMP-SWG-VT-ACC
                            p(f"{S} Part 2.3.7.C",
                              "Voltage transformers shall have accuracy class 0.5 for metering and 3P "
                              "for protection. Primary voltage shall be 11 kV/√3, secondary 110 V/√3."),
                        ],
                    },
                ],
            },
            {
                "part": 3,
                "title": "EXECUTION",
                "articles": [
                    {
                        "number": "3.1",
                        "title": "Installation",
                        "paragraphs": [
                            p(f"{S} Part 3.1.1.A",
                              "Switchgear shall be installed on prepared foundations with adequate "
                              "clearances per manufacturer recommendations. Minimum front clearance "
                              "shall be 2000 mm. Minimum rear clearance shall be 1000 mm."),
                        ],
                    },
                    {
                        "number": "3.2",
                        "title": "Field Quality Control",
                        "paragraphs": [
                            p(f"{S} Part 3.2.1.A",
                              "Perform insulation resistance tests on all busbars and cable terminations "
                              "prior to energisation. Minimum acceptable IR value is 1000 MΩ at 5 kV DC."),
                        ],
                    },
                ],
            },
        ],
    }


def build_23_81_23():
    """Section 23 81 23 - Computer Room Air Handling Units."""
    S = "23 81 23"
    return {
        "title": "Computer Room Air Handling Units",
        "parts": [
            {
                "part": 1,
                "title": "GENERAL",
                "articles": [
                    {
                        "number": "1.1",
                        "title": "Summary",
                        "paragraphs": [
                            p(f"{S} Part 1.1.1.A",
                              "This section specifies the requirements for chilled water Computer Room "
                              "Air Handling (CRAH) units for the Meridian Data Centre Campus, Phase 1. "
                              "CRAH units shall provide precision sensible cooling to each Server Hall "
                              "using the campus chilled water plant."),
                        ],
                    },
                    {
                        "number": "1.2",
                        "title": "References",
                        "paragraphs": [
                            p(f"{S} Part 1.2.1.A",
                              "The following standards shall apply: AHRI 1360 (Performance Rating of "
                              "Computer and Data Processing Room Air Conditioners), ASHRAE 90.1 (Energy "
                              "Standard for Buildings), IS 1391 (Room Air Conditioners), ASHRAE TC 9.9 "
                              "(Thermal Guidelines for Data Processing Environments)."),
                        ],
                    },
                    {
                        "number": "1.3",
                        "title": "Submittal Requirements",
                        "paragraphs": [
                            p(f"{S} Part 1.3.1.A",
                              "Submittals shall include certified cooling capacity data, airflow "
                              "performance curves, chilled water coil ratings, fan performance data, "
                              "dimensional drawings, electrical data, and BMS integration details."),
                        ],
                    },
                    {
                        "number": "1.4",
                        "title": "Quality Assurance",
                        "paragraphs": [
                            p(f"{S} Part 1.4.1.A",
                              "CRAH manufacturer shall have a minimum of 10 years experience in the "
                              "manufacture of precision cooling systems for mission-critical data centre "
                              "environments. Manufacturer shall hold ISO 9001 certification."),
                        ],
                    },
                ],
            },
            {
                "part": 2,
                "title": "PRODUCTS",
                "articles": [
                    {
                        "number": "2.1",
                        "title": "Acceptable Manufacturers",
                        "paragraphs": [
                            p(f"{S} Part 2.1.1.A",
                              "Acceptable CRAH manufacturers: CryoCore Climate, or approved equivalent "
                              "meeting all performance requirements of this section."),
                        ],
                    },
                    {
                        "number": "2.2",
                        "title": "Performance and Design Criteria",
                        "paragraphs": [
                            # REQUIRED: COMP-CRAH-CAP
                            p(f"{S} Part 2.2.1.A",
                              "Each CRAH unit shall provide a minimum sensible cooling capacity of "
                              "250 kW at the design conditions specified herein."),
                            # REQUIRED: COMP-CRAH-CHW-IN (Addendum 3 changes this)
                            p(f"{S} Part 2.2.1.B",
                              "Design entering chilled water temperature shall be 10°C. The CRAH "
                              "cooling coil shall be selected and rated at this entering water "
                              "temperature."),
                            # REQUIRED: COMP-CRAH-CHW-OUT
                            p(f"{S} Part 2.2.1.C",
                              "Design leaving chilled water temperature shall be 18°C, resulting in a "
                              "chilled water temperature differential (delta-T) of 8 K across the cooling "
                              "coil."),
                            # REQUIRED: DEV-CRAH-AIRFLOW
                            p(f"{S} Part 2.2.2.A",
                              "Minimum unit airflow rate shall be 64,320 m³/h at the design external "
                              "static pressure. Airflow shall be measured at the unit discharge per "
                              "AHRI 1360 test conditions."),
                            p(f"{S} Part 2.2.3.A",
                              "Supply air temperature shall be 23°C +/- 1°C at design conditions. Return "
                              "air temperature shall be 35°C maximum under hot aisle containment."),
                            p(f"{S} Part 2.2.4.A",
                              "Total cooling capacity (sensible plus latent) shall be submitted along "
                              "with the sensible heat ratio (SHR) at design conditions."),
                            p(f"{S} Part 2.2.4.B",
                              "Cooling capacity shall be verified by the manufacturer at the specified "
                              "entering and leaving water temperatures and air conditions."),
                            # DEF-004: COP with no operating conditions
                            p(f"{S} Part 2.2.4.C",
                              "Unit coefficient of performance (COP) shall be a minimum of 5.2. "
                              "The vendor shall submit the COP value as part of the performance data "
                              "submittal."),
                            # REQUIRED: COMP-CRAH-HUMIDITY-RANGE
                            p(f"{S} Part 2.2.5",
                              "CRAH unit shall maintain operation across a relative humidity range of "
                              "20% to 80% non-condensing within the server room environment. Humidity "
                              "control shall be integrated with the unit controller."),
                            p(f"{S} Part 2.2.6.A",
                              "CRAH unit controller shall provide proportional-integral (PI) control of "
                              "supply air temperature with adjustable setpoints. Controller shall support "
                              "Modbus TCP/IP and BACnet communication protocols."),
                            p(f"{S} Part 2.2.7.A",
                              "Unit shall include high-efficiency air filters with a minimum MERV 11 "
                              "rating. Filter frames shall be accessible for replacement without tools."),
                            # REQUIRED: DEV-CRAH-REFRIGERANT
                            p(f"{S} Part 2.2.8",
                              "Where the CRAH unit incorporates a direct expansion (DX) trim cooling "
                              "circuit, the refrigerant type shall be R-410A only. Use of R-407C, R-22, "
                              "or any other refrigerant is not permitted."),
                        ],
                    },
                    {
                        "number": "2.3",
                        "title": "Component Description",
                        "paragraphs": [
                            p(f"{S} Part 2.3.1.A",
                              "Chilled water cooling coil shall be copper tube with aluminium or copper "
                              "fins. Coil shall be leak tested at the factory at 1.5 times working "
                              "pressure. Coil connections shall be flanged."),
                            # REQUIRED: COMP-CRAH-FAN-EFF
                            p(f"{S} Part 2.3.2.A",
                              "CRAH unit fans shall be electronically commutated (EC) type with variable "
                              "speed drive. Fan motor power density shall be less than 0.10 W per m³/h "
                              "of airflow at design conditions."),
                            # REQUIRED: DEV-CRAH-UNIT-HP
                            p(f"{S} Part 2.3.2.B",
                              "Fan motor power shall be specified in electrical kilowatts (kW). "
                              "Specifications of motor power in alternative units (HP, BHP, or PS) "
                              "shall not be accepted."),
                            p(f"{S} Part 2.3.3.A",
                              "Fan assemblies shall be direct-drive with integrated EC motors. Belt-driven "
                              "fan arrangements are not acceptable."),
                            p(f"{S} Part 2.3.4.A",
                              "Unit shall include a condensate drain pan of stainless steel construction "
                              "with dual drain connections. Drain pan shall be insulated to prevent "
                              "external condensation."),
                            # REQUIRED: DEV-CRAH-MISS-PARAM
                            p(f"{S} Part 2.3.5.A",
                              "CRAH unit shall be equipped with a 2-way modulating control valve for "
                              "chilled water flow regulation. The valve flow coefficient (Cv) shall be "
                              "specified and submitted for hydraulic circuit balancing calculations."),
                            p(f"{S} Part 2.3.5.B",
                              "Control valve actuator shall be spring-return, fail-closed type with "
                              "a modulating signal range of 0-10 VDC or 4-20 mA."),
                            # REQUIRED: DEV-CRAH-VALVE-TYPE
                            p(f"{S} Part 2.3.5.C",
                              "Chilled water flow regulation shall utilise pressure independent control "
                              "valves (PICV) to ensure consistent flow regulation regardless of system "
                              "pressure variations. Standard 2-way modulating valves without pressure "
                              "independence are not acceptable."),
                            p(f"{S} Part 2.3.6.A",
                              "Unit shall include onboard humidity sensing with dry bulb and dew point "
                              "temperature sensors."),
                            # REQUIRED: DEV-CRAH-HUMIDIFIER
                            p(f"{S} Part 2.3.6.B",
                              "Humidity control shall be provided by an electrode steam generating "
                              "humidifier integrated within the CRAH unit. Infrared, ultrasonic, or "
                              "spray-type humidifier systems are not acceptable."),
                        ],
                    },
                    {
                        "number": "2.4",
                        "title": "Physical Construction",
                        "paragraphs": [
                            # REQUIRED: DEV-CRAH-WIDTH
                            p(f"{S} Part 2.4.1.A",
                              "CRAH unit overall cabinet width shall not exceed 2400 mm to ensure "
                              "transport clearance through standard data centre corridors and freight "
                              "elevator openings. Units exceeding this width shall not be accepted."),
                            p(f"{S} Part 2.4.1.B",
                              "Cabinet construction shall be double-skin insulated panels with powder "
                              "coated galvanised steel exterior finish. Internal lining shall be "
                              "acoustically treated."),
                            p(f"{S} Part 2.4.2.A",
                              "Unit shall be suitable for underfloor air discharge configuration with "
                              "bottom discharge plenum. Side return air inlet arrangement shall be "
                              "provided."),
                        ],
                    },
                ],
            },
            {
                "part": 3,
                "title": "EXECUTION",
                "articles": [
                    {
                        "number": "3.1",
                        "title": "Examination and Preparation",
                        "paragraphs": [
                            p(f"{S} Part 3.1.1.A",
                              "Verify that chilled water piping, floor grilles, and electrical "
                              "connections are complete and ready prior to CRAH unit placement."),
                        ],
                    },
                    {
                        "number": "3.2",
                        "title": "Installation",
                        "paragraphs": [
                            p(f"{S} Part 3.2.1.A",
                              "CRAH units shall be placed on anti-vibration pads on the prepared raised "
                              "floor structure. Chilled water connections shall be made with flexible "
                              "connectors and isolation valves."),
                        ],
                    },
                    {
                        "number": "3.3",
                        "title": "Field Testing and Commissioning",
                        "paragraphs": [
                            p(f"{S} Part 3.3.1.A",
                              "Perform chilled water system flushing and water quality verification "
                              "prior to CRAH unit startup."),
                            # REQUIRED: CX-CRAH-L4-01 and CX-TEST-L4-02 through L4-10
                            p(f"{S} Part 3.3.2.A",
                              "Verify sensible cooling capacity is a minimum of 250 kW at the specified "
                              "entering chilled water temperature. Measurements shall use calibrated "
                              "temperature sensors and flow meters."),
                            p(f"{S} Part 3.3.2.B",
                              "Verify chilled water flow rate through the CRAH cooling coil matches the "
                              "design value within +/- 10%. Flow shall be measured using an ultrasonic "
                              "flow meter."),
                            p(f"{S} Part 3.3.2.C",
                              "Verify entering and leaving chilled water temperatures match the design "
                              "basis values. Temperature measurements shall use calibrated RTD sensors "
                              "with accuracy of +/- 0.1°C."),
                            p(f"{S} Part 3.3.2.D",
                              "Verify supply air temperature is within the specified tolerance of "
                              "23°C +/- 1°C at design load conditions."),
                            p(f"{S} Part 3.3.2.E",
                              "Verify unit airflow rate at design external static pressure using a "
                              "calibrated airflow measurement station or traverse method per ASHRAE 111."),
                            p(f"{S} Part 3.3.2.F",
                              "Verify EC fan motor current draw is within the nameplate rating. Fan speed "
                              "shall be set to achieve the specified airflow rate."),
                            p(f"{S} Part 3.3.2.G",
                              "Verify humidity control operation. Humidifier shall maintain room humidity "
                              "within the specified range during the test period."),
                            p(f"{S} Part 3.3.2.H",
                              "Verify BMS communication and alarm integration. All critical alarms "
                              "(high supply temperature, low airflow, chilled water leak, filter "
                              "differential pressure) shall be confirmed operational."),
                            p(f"{S} Part 3.3.2.I",
                              "Verify condensate drain system operation under full cooling load. Drain "
                              "pan shall show no evidence of overflow or leakage during the test."),
                            p(f"{S} Part 3.3.2.J",
                              "Perform 72-hour continuous run test under simulated IT load. CRAH unit "
                              "shall maintain stable supply air temperature throughout the test period "
                              "without nuisance alarms or shutdowns."),
                        ],
                    },
                ],
            },
        ],
    }


def build_21_22_00():
    """Section 21 22 00 - Clean Agent Fire Suppression Systems."""
    S = "21 22 00"
    return {
        "title": "Clean Agent Fire Suppression Systems",
        "parts": [
            {
                "part": 1,
                "title": "GENERAL",
                "articles": [
                    {
                        "number": "1.1",
                        "title": "Summary",
                        "paragraphs": [
                            p(f"{S} Part 1.1.1.A",
                              "This section specifies the requirements for clean agent fire suppression "
                              "systems using FK-5-1-12 (Dodecafluoro-2-methylpentan-3-one) for server rooms "
                              "and critical electrical rooms at the Meridian Data Centre Campus, Phase 1."),
                            p(f"{S} Part 1.1.1.B",
                              "The clean agent system shall provide total flooding fire suppression for "
                              "Class A (ordinary combustibles) and Class C (energised electrical equipment) "
                              "hazards. The system shall be safe for use in occupied spaces."),
                        ],
                    },
                    {
                        "number": "1.2",
                        "title": "References",
                        "paragraphs": [
                            # DEF-006: cites NFPA 2001 (2008 Edition) - obsolete
                            p(f"{S} Part 1.2.1",
                              "The clean agent fire suppression system shall be designed, installed, and "
                              "tested in accordance with NFPA 2001 (2008 Edition) - Standard on Clean Agent "
                              "Fire Extinguishing Systems. All system components shall comply with the "
                              "requirements of this standard."),
                            p(f"{S} Part 1.2.2.A",
                              "Additional applicable standards include: IS 15493 (Clean Agent Fire "
                              "Extinguishing Systems), NBC Part 4 (Fire and Life Safety), and the local "
                              "fire department regulations of Navi Mumbai Municipal Corporation."),
                            # REQUIRED: DEV-FIRE-STANDARDS
                            p(f"{S} Part 1.2.3",
                              "All clean agent storage cylinders and discharge valve assemblies shall be "
                              "tested, listed, and labeled in accordance with UL 2166 (Halocarbon Clean "
                              "Agent Extinguishing System Units) and FM 5600 (Clean Agent Extinguishing "
                              "Systems). Cylinders certified only to ISO 9809-1 without UL and FM "
                              "listing shall not be accepted."),
                        ],
                    },
                    {
                        "number": "1.3",
                        "title": "Submittal Requirements",
                        "paragraphs": [
                            p(f"{S} Part 1.3.1.A",
                              "Submittals shall include system design calculations, agent quantity "
                              "calculations, hydraulic flow calculations, nozzle layout drawings, "
                              "detection zone drawings, and control panel wiring diagrams."),
                            p(f"{S} Part 1.3.2.A",
                              "A room integrity (door fan) test report shall be submitted for each "
                              "protected enclosure, demonstrating the required agent hold time."),
                            # REQUIRED: DEV-FIRE-CERT-MISS
                            p(f"{S} Part 1.3.3",
                              "Factory test and compliance certificates issued by UL and FM for all "
                              "clean agent storage cylinder valve assemblies shall be submitted as part "
                              "of the vendor submittal package. Submittals without these certificates "
                              "shall be considered incomplete."),
                        ],
                    },
                    {
                        "number": "1.4",
                        "title": "Quality Assurance",
                        "paragraphs": [
                            p(f"{S} Part 1.4.1.A",
                              "System designer shall be a licensed fire protection engineer registered "
                              "with the relevant statutory authority. The designer shall have a minimum "
                              "of 5 installations of clean agent systems in data centre environments."),
                        ],
                    },
                ],
            },
            {
                "part": 2,
                "title": "PRODUCTS",
                "articles": [
                    {
                        "number": "2.1",
                        "title": "Clean Agent System",
                        "paragraphs": [
                            # REQUIRED: COMP-FIRE-AGENT
                            p(f"{S} Part 2.1.1",
                              "The clean agent shall be FK-5-1-12 (Dodecafluoro-2-methylpentan-3-one), "
                              "chemically identified as CF3CF2C(O)CF(CF3)2. The agent shall have zero "
                              "ozone depletion potential (ODP) and a global warming potential (GWP) of 1. "
                              "No alternative agents shall be substituted without written approval."),
                        ],
                    },
                    {
                        "number": "2.2",
                        "title": "System Performance Requirements",
                        "paragraphs": [
                            # REQUIRED: COMP-FIRE-CONC
                            p(f"{S} Part 2.2.1",
                              "Design concentration shall be 4.7% by volume (v/v) for Class A and "
                              "Class C fire hazards. The design concentration shall be maintained "
                              "uniformly throughout the protected enclosure volume within the agent "
                              "hold time period."),
                            # REQUIRED: COMP-FIRE-NOAEL
                            p(f"{S} Part 2.2.2",
                              "The No Observed Adverse Effect Level (NOAEL) for FK-5-1-12 is 10.0% "
                              "by volume (v/v). The design concentration of 4.7% provides a safety "
                              "margin well below the NOAEL, ensuring the system is safe for occupied "
                              "spaces without pre-discharge personnel evacuation."),
                            # REQUIRED: DEV-FIRE-DISCH-FOOT
                            p(f"{S} Part 2.2.3.A",
                              "Clean agent discharge time shall not exceed 10 seconds from the moment "
                              "the discharge valve opens until 95% of the design agent quantity has been "
                              "released into the protected enclosure, per NFPA 2001 requirements."),
                            # REQUIRED: DEV-FIRE-HOLDTIME
                            p(f"{S} Part 2.2.3.B",
                              "Agent hold time (retention) shall be a minimum of 10 minutes (600 seconds) "
                              "to prevent re-ignition. Hold time shall be verified by a room integrity "
                              "(door fan) test conducted per NFPA 2001 Annex C."),
                            p(f"{S} Part 2.2.4.A",
                              "System shall include automatic detection using cross-zoned smoke detectors "
                              "(two detectors in alarm required for discharge). Manual pull stations shall "
                              "be provided at each exit."),
                            # REQUIRED: DEV-FIRE-QUANTITY
                            p(f"{S} Part 2.2.5",
                              "Minimum total clean agent quantity for the campus shall be 12,500 kg of "
                              "FK-5-1-12. Agent quantity per zone shall be determined by the design "
                              "concentration, protected volume, and altitude correction factors per "
                              "NFPA 2001 calculation methodology."),
                        ],
                    },
                    {
                        "number": "2.3",
                        "title": "System Components",
                        "paragraphs": [
                            # REQUIRED: DEV-FIRE-PRESSURE
                            p(f"{S} Part 2.3.1.A",
                              "Clean agent storage cylinders shall be pressurised to 500 psi (34.5 bar) "
                              "with nitrogen super-pressurisation. The system configuration shall be "
                              "ECS-500 type with high-pressure distribution for optimal nozzle coverage "
                              "and discharge performance."),
                            p(f"{S} Part 2.3.1.B",
                              "Cylinder valve assemblies shall be UL listed and FM approved. Valves shall "
                              "include a manual safety pin, pressure gauge, and electric solenoid actuator."),
                            p(f"{S} Part 2.3.2.A",
                              "Distribution piping shall be Schedule 40 galvanised steel per ASTM A53. "
                              "Pipe sizing shall be per NFPA 2001 hydraulic calculations to achieve the "
                              "required discharge time."),
                            p(f"{S} Part 2.3.3.A",
                              "Discharge nozzles shall be 360-degree pattern type designed specifically "
                              "for FK-5-1-12 agent. Nozzle coverage shall be as per manufacturer's "
                              "approved layout based on ceiling height and room geometry."),
                            p(f"{S} Part 2.3.4.A",
                              "Control panel shall be UL/FM listed, with zone identification, alarm "
                              "history, and supervisory signal monitoring capabilities."),
                            p(f"{S} Part 2.3.4.B",
                              "Pre-discharge audible and visual alarm devices shall be installed inside "
                              "each protected space. Alarm shall provide a minimum of 30 seconds warning "
                              "prior to agent discharge."),
                            p(f"{S} Part 2.3.4.C",
                              "Post-discharge exhaust fan system shall be provided to evacuate agent "
                              "and combustion byproducts from the protected space. Exhaust rate shall "
                              "achieve 6 air changes per hour minimum."),
                            p(f"{S} Part 2.3.4.D",
                              "Pressure relief venting shall be provided in each protected enclosure "
                              "to prevent structural damage during rapid agent discharge. Vent area "
                              "shall be calculated per NFPA 2001 guidelines."),
                            p(f"{S} Part 2.3.4.E",
                              "System shall include abort switches at each exit door allowing personnel "
                              "to delay agent discharge during the pre-discharge alarm period."),
                            # REQUIRED: DEV-FIRE-MISS-PARAM
                            p(f"{S} Part 2.3.4.F",
                              "The vendor shall submit a NOAEL safety margin calculation demonstrating "
                              "that the actual maximum agent concentration in the protected space does "
                              "not exceed the NOAEL limit of 10.0% (v/v) under worst-case conditions "
                              "including altitude and temperature corrections."),
                        ],
                    },
                ],
            },
            {
                "part": 3,
                "title": "EXECUTION",
                "articles": [
                    {
                        "number": "3.1",
                        "title": "Examination and Preparation",
                        "paragraphs": [
                            p(f"{S} Part 3.1.1.A",
                              "Verify that all room envelope penetrations are sealed and room integrity "
                              "is maintained prior to system installation. Coordinate with architectural "
                              "and mechanical trades."),
                        ],
                    },
                    {
                        "number": "3.2",
                        "title": "Installation",
                        "paragraphs": [
                            p(f"{S} Part 3.2.1.A",
                              "Clean agent piping shall be installed with adequate supports and expansion "
                              "provisions. All piping joints shall be threaded or groove-coupled as "
                              "specified by the system manufacturer."),
                        ],
                    },
                    {
                        "number": "3.3",
                        "title": "Field Quality Control",
                        "paragraphs": [
                            p(f"{S} Part 3.3.1.A",
                              "Pneumatic pressure test all agent distribution piping at 1.5 times the "
                              "maximum storage cylinder pressure. Hold time shall be 24 hours with no "
                              "measurable pressure drop."),
                        ],
                    },
                    {
                        "number": "3.4",
                        "title": "Commissioning and Acceptance",
                        "paragraphs": [
                            # REQUIRED: CX-FIRE-L5-01
                            p(f"{S} Part 3.4.1",
                              "Perform system functional test verifying agent discharge completion within "
                              "10 seconds of system activation. Test shall be conducted using a simulated "
                              "discharge (nitrogen blow-through) or full live discharge per the approved "
                              "commissioning test plan."),
                            p(f"{S} Part 3.4.2.A",
                              "Conduct a room integrity (door fan) test to verify the agent hold time "
                              "meets the minimum requirement. Test report shall be prepared by a qualified "
                              "fire protection technician."),
                        ],
                    },
                ],
            },
        ],
    }


def build_all_clauses():
    """Build the complete clauses dict for all 6 sections."""
    return {
        "26 05 00": build_26_05_00(),
        "26 33 53": build_26_33_53(),
        "26 32 13": build_26_32_13(),
        "26 13 26": build_26_13_26(),
        "23 81 23": build_23_81_23(),
        "21 22 00": build_21_22_00(),
    }


def count_clauses(clauses_data):
    """Count total clause entries."""
    total = 0
    for section_data in clauses_data.values():
        for part in section_data.get("parts", []):
            for article in part.get("articles", []):
                total += len(article.get("paragraphs", []))
    return total


def collect_clause_ids(clauses_data):
    """Collect all clause_ids from the clauses data."""
    ids = set()
    for section_data in clauses_data.values():
        for part in section_data.get("parts", []):
            for article in part.get("articles", []):
                for para in article.get("paragraphs", []):
                    ids.add(para["clause_id"])
    return ids


def main():
    # Check if clauses already exist
    with open(BIBLE_PATH, "r") as f:
        content = f.read()
    if "\nclauses:" in content or content.startswith("clauses:"):
        print("ERROR: clauses block already exists in project_bible.yaml")
        return 1

    # Build clauses
    clauses_data = build_all_clauses()
    clause_ids = collect_clause_ids(clauses_data)
    total = count_clauses(clauses_data)

    # Check for duplicate clause_ids
    all_ids = []
    for section_data in clauses_data.values():
        for part in section_data.get("parts", []):
            for article in part.get("articles", []):
                for para in article.get("paragraphs", []):
                    all_ids.append(para["clause_id"])
    if len(all_ids) != len(set(all_ids)):
        dupes = [cid for cid in all_ids if all_ids.count(cid) > 1]
        print(f"ERROR: Duplicate clause_ids found: {set(dupes)}")
        return 1

    # Serialize and append
    clauses_yaml = yaml.dump(
        {"clauses": clauses_data},
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=120,
    )

    with open(BIBLE_PATH, "a") as f:
        f.write("\n")
        f.write(clauses_yaml)

    print(f"Successfully appended clauses block to {BIBLE_PATH}")
    print(f"  Sections: {len(clauses_data)}")
    print(f"  Total clauses: {total}")
    print(f"  Unique clause_ids: {len(clause_ids)}")

    # Quick validation: reload and verify
    with open(BIBLE_PATH, "r") as f:
        bible = yaml.safe_load(f)

    if "clauses" not in bible:
        print("ERROR: clauses block not found after append!")
        return 1

    reloaded_count = count_clauses(bible["clauses"])
    print(f"  Verified after reload: {reloaded_count} clauses")

    # Verify existing top-level keys are intact
    expected_keys = {"project", "timeline", "rules", "submittal_packages",
                     "spec_defects", "addendum_3", "deviations",
                     "compliant_checks", "equipment", "registers", "clauses"}
    actual_keys = set(bible.keys())
    if not expected_keys.issubset(actual_keys):
        missing = expected_keys - actual_keys
        print(f"ERROR: Missing top-level keys after append: {missing}")
        return 1

    print("  All existing top-level keys verified intact.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
