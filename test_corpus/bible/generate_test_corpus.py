#!/usr/bin/env python3
import os
import sys
import csv

def write_pdf(filepath, pages_lines):
    """
    Generate a simple standard, text-only PDF file using a pure Python PDF generator.
    Uses monospaced Courier font to preserve alignment of tables and compliance matrices.
    """
    body = []
    offsets = {}
    P = len(pages_lines)
    
    # 1. Header
    body.append(b'%PDF-1.4\n')
    
    # 2. Catalog (Object 1)
    offsets[1] = sum(len(x) for x in body)
    body.append(b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n')
    
    # 3. Pages (Object 2)
    kids_refs = " ".join(f"{4 + i} 0 R" for i in range(P))
    offsets[2] = sum(len(x) for x in body)
    body.append(f'2 0 obj\n<< /Type /Pages /Kids [ {kids_refs} ] /Count {P} >>\nendobj\n'.encode('latin1'))
    
    # 4. Font (Object 3) - Use monospaced Courier to preserve ASCII structure
    offsets[3] = sum(len(x) for x in body)
    body.append(b'3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>\nendobj\n')
    
    # 5. Page objects (Objects 4 to 4 + P - 1)
    for i in range(P):
        obj_id = 4 + i
        content_id = 4 + P + i
        offsets[obj_id] = sum(len(x) for x in body)
        body.append(f'{obj_id} 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 3 0 R >> >> /MediaBox [0 0 595 842] /Contents {content_id} 0 R >>\nendobj\n'.encode('latin1'))
        
    # 6. Content streams (Objects 4 + P to 4 + 2*P - 1)
    for i in range(P):
        obj_id = 4 + P + i
        lines = pages_lines[i]
        
        # Build text stream
        stream_parts = ["BT", "/F1 10 Tf", "12 TL", "50 790 Td"]
        for line in lines:
            escaped_line = line.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
            stream_parts.append(f"({escaped_line}) Tj T*")
        stream_parts.append("ET")
        stream_content = "\n".join(stream_parts).encode('utf-8')
        
        offsets[obj_id] = sum(len(x) for x in body)
        body.append(f'{obj_id} 0 obj\n<< /Length {len(stream_content)} >>\nstream\n'.encode('latin1'))
        body.append(stream_content)
        body.append(b'\nendstream\nendobj\n')
        
    # 7. Cross-reference table (xref)
    xref_pos = sum(len(x) for x in body)
    body.append(b'xref\n')
    num_objects = 4 + 2 * P
    body.append(f'0 {num_objects}\n'.encode('latin1'))
    body.append(b'0000000000 65535 f \n')
    for obj_id in range(1, num_objects):
        pos = offsets[obj_id]
        body.append(f'{pos:010d} 00000 n \n'.encode('latin1'))
        
    # 8. Trailer
    body.append(f'trailer\n<< /Size {num_objects} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n'.encode('latin1'))
    
    with open(filepath, 'wb') as f:
        f.writelines(body)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    corpus_root = os.path.dirname(script_dir)
    
    # Create subdirectories under test_corpus/
    subdirs = ["specs", "submittals", "addenda", "registers", "project_docs"]
    for d in subdirs:
        os.makedirs(os.path.join(corpus_root, d), exist_ok=True)
        
    print(f"Initialized directories under {corpus_root}/")

    # Define all documents inline
    specs = {
        "26_05_00": {
            "title": "Common Work Results for Electrical",
            "clauses": [
                {"id": "26 05 00 Part 1.2.1.A", "text": "All fire alarm and electrical installations shall comply with NFPA 2001 (2008 Edition)."},
                {"id": "26 05 00 Part 1.4.3.B", "text": "All medium voltage equipment and switchgear assemblies shall be type tested and certified in accordance with the applicable IEC standards. IEC type test certificates from ASTA or KEMA shall be provided."}
            ]
        },
        "26_33_53": {
            "title": "Static Uninterruptible Power Supply",
            "clauses": [
                {"id": "26 33 53 Part 2.1.2.A", "text": "The UPS system shall be configured with N+2 redundancy."},
                {"id": "26 33 53 Part 2.3.4", "text": "Inverter efficiency shall be not less than 96.0 percent at full load."},
                {"id": "26 33 53 Part 2.3.1.E", "text": "Battery runtime at full load shall be a minimum of 10.0 minutes."},
                {"id": "26 33 53 Part 3.4.2.C", "text": "Battery runtime at full load shall be a minimum of 12 minutes."},
                {"id": "26 33 53 Part 2.2.4.C", "text": "The UPS system shall achieve a minimum COP of 5.2."},
                {"id": "26 33 53 Part 1.5.1.A", "text": "The contractor shall provide adequate warranty coverage for all system components."}
            ]
        },
        "26_32_13": {
            "title": "Engine Generators",
            "clauses": [
                {"id": "26 32 13 Part 3.2.1.F", "text": "Fuel day tanks located indoors shall have a minimum capacity of 1200 litres."}
            ]
        },
        "26_13_26": {
            "title": "Medium Voltage Switchgear",
            "clauses": [
                {"id": "26 13 26 Part 1.2.1", "text": "Medium voltage switchgear shall be certified in accordance with UL 347."}
            ]
        }
    }

    # 1. Generate Specs (PDF + HTML)
    for section_stem, sec_data in specs.items():
        section = section_stem.replace("_", " ")
        title = sec_data["title"]
        clauses = sec_data["clauses"]
        
        # Build HTML content
        html_lines = [
            "<!DOCTYPE html>",
            "<html>",
            f"<head><title>Section {section} - {title}</title></head>",
            "<body>",
            f"<h1>SECTION {section}</h1>",
            f"<h2>{title.upper()}</h2>",
            "<h3>PART 1 - GENERAL</h3>",
            "<p>PART 1 - GENERAL requirements are specified here.</p>",
            "<h3>PART 2 - PRODUCTS</h3>"
        ]
        
        # Split into PDF pages
        pdf_pages = []
        current_page_lines = [
            f"SECTION {section}",
            f"{title.upper()}",
            "PART 1 - GENERAL",
            "1.1 SUMMARY",
            f"  This section covers the requirements for the {title}.",
            "PART 2 - PRODUCTS"
        ]
        
        for c in clauses:
            clause_id = c["id"]
            text = c["text"]
            line_str = f"{clause_id} {text}"
            html_lines.append(f"<p>{line_str}</p>")
            current_page_lines.append(line_str)
            if len(current_page_lines) > 40:
                pdf_pages.append(current_page_lines)
                current_page_lines = []
                
        if current_page_lines:
            pdf_pages.append(current_page_lines)
            
        html_lines.extend(["</body>", "</html>"])
        
        # Write HTML
        html_path = os.path.join(corpus_root, "specs", f"spec_{section_stem}.html")
        with open(html_path, "w", encoding="utf-8") as hf:
            hf.write("\n".join(html_lines))
            
        # Write PDF
        pdf_path = os.path.join(corpus_root, "specs", f"spec_{section_stem}.pdf")
        write_pdf(pdf_path, pdf_pages)
        print(f"Generated spec spec_{section_stem}.pdf and spec_{section_stem}.html")

    # 2. Generate Submittals (PDF)
    submittals = [
        {
            "filename": "submittal_VoltEdge_UPS_R0.pdf",
            "pages": [
                [
                    "VoltEdge UPS System Submittal - R0",
                    "Reference Section: 26 33 53",
                    "Package ID: SUB-263353-01-R0",
                    "Revision: R0",
                    "Reviewed Spec Revision: Rev 2024",
                    "Date: 01-01-2025"
                ],
                [
                    "Technical Datasheet - VoltEdge UPS System",
                    "---------------------------------------------------------",
                    "| Parameter                 | Value   | Operating Condition   |",
                    "---------------------------------------------------------",
                    "| Inverter Efficiency       | 95.5%   | Full load             |",
                    "| Inverter Efficiency       | 94.2%   | 50% load              |",
                    "| UPS System Redundancy    | N+1     | Standard config       |",
                    "| Battery Runtime           | 10 min  | Full load discharge   |",
                    "---------------------------------------------------------"
                ],
                [
                    "Compliance Matrix - VoltEdge UPS System",
                    "-----------------------------------------------------------------------",
                    "| Clause Reference       | Requirement Summary | Stated Response | Stance   |",
                    "-----------------------------------------------------------------------",
                    "| 26 33 53 Part 2.1.2.A  | N+2 Redundancy       | Comply          | Compliant|",
                    "| 26 33 53 Part 2.3.4    | Efficiency >= 96.0% | Comply          | Compliant|",
                    "-----------------------------------------------------------------------"
                ]
            ]
        },
        {
            "filename": "submittal_VoltEdge_UPS_R1.pdf",
            "pages": [
                [
                    "VoltEdge UPS System Submittal - R1",
                    "Reference Section: 26 33 53",
                    "Package ID: SUB-263353-01-R1",
                    "Revision: R1",
                    "Reviewed Spec Revision: Rev 2024",
                    "Date: 02-15-2025"
                ],
                [
                    "Technical Datasheet - VoltEdge UPS System",
                    "---------------------------------------------------------",
                    "| Parameter                 | Value   | Operating Condition   |",
                    "---------------------------------------------------------",
                    "| Inverter Efficiency       | 96.2%   | Full load             |",
                    "| UPS System Redundancy    | N+2     | Standard config       |",
                    "| Battery Runtime           | 10 min  | Full load discharge   |",
                    "---------------------------------------------------------"
                ],
                [
                    "Compliance Matrix - VoltEdge UPS System",
                    "-----------------------------------------------------------------------",
                    "| Clause Reference       | Requirement Summary | Stated Response | Stance   |",
                    "-----------------------------------------------------------------------",
                    "| 26 33 53 Part 2.1.2.A  | N+2 Redundancy       | Comply          | Compliant|",
                    "| 26 33 53 Part 2.3.4    | Efficiency >= 96.0% | Comply          | Compliant|",
                    "-----------------------------------------------------------------------"
                ]
            ]
        }
    ]

    for sub in submittals:
        filename = sub["filename"]
        pdf_path = os.path.join(corpus_root, "submittals", filename)
        write_pdf(pdf_path, sub["pages"])
        print(f"Generated submittal {filename}")

    # 3. Generate Addenda (PDF)
    addenda = [
        {
            "filename": "addendum_3.pdf",
            "pages": [
                [
                    "ADDENDUM NO. 3",
                    "Date: 2026-06-15",
                    "Project: TEST_DATA_CENTRE",
                    "",
                    "Reference: Section 26 33 53, Part 2.3.4",
                    "Action: DELETE 'not less than 96.0 percent' and INSERT 'not less than 96.5 percent'",
                    "Clause: Inverter efficiency is upgraded to 96.5 percent."
                ]
            ]
        }
    ]

    for add in addenda:
        filename = add["filename"]
        pdf_path = os.path.join(corpus_root, "addenda", filename)
        write_pdf(pdf_path, add["pages"])
        print(f"Generated addendum {filename}")

    # 4. Generate Project Docs (PDF)
    project_docs = [
        {
            "filename": "design_basis_report.pdf",
            "pages": [
                [
                    "Design Basis Report - TEST_DATA_CENTRE",
                    "Redundancy requirements for electrical systems:",
                    "We specify N+2 redundancy for static UPS systems."
                ]
            ]
        },
        {
            "filename": "kickoff_minutes.pdf",
            "pages": [
                [
                    "Project Kickoff Meeting Minutes",
                    "Project name: TEST_DATA_CENTRE",
                    "Date: 2024-12-01"
                ]
            ]
        }
    ]

    for doc in project_docs:
        filename = doc["filename"]
        pdf_path = os.path.join(corpus_root, "project_docs", filename)
        write_pdf(pdf_path, doc["pages"])
        print(f"Generated project document {filename}")

    # 5. Generate Registers (CSVs)
    # po_register.csv
    po_path = os.path.join(corpus_root, "registers", "po_register.csv")
    with open(po_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["po_number", "equipment_tag", "spec_section", "vendor", "item_description", "value_inr", "order_date", "lead_time_weeks", "delivery_status"])
        writer.writerow(["PO-263353-H1", "UPS-01-01", "26 33 53", "VoltEdge Power Systems", "VoltEdge PX-1200 UPS Module 1200kW Hall 1", "25000000", "2026-01-10", "24", "DELIVERED"])
        writer.writerow(["PO-263213-G1", "GEN-01-01", "26 32 13", "Deccan Diesel Co.", "Deccan DD-2500 Generator Set 2500kVA Hall 1", "38000000", "2026-01-15", "40", "IN_TRANSIT"])
    print("Generated po_register.csv")
            
    # schedule.csv
    sched_path = os.path.join(corpus_root, "registers", "schedule.csv")
    with open(sched_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["activity_id", "name", "duration_days", "predecessors", "float_days", "critical_path"])
        writer.writerow(["ACT-CIV-01", "Civil Works Phase 1", "15", "", "0", "True"])
        writer.writerow(["ACT-ELE-GEN-01", "Procure and Deliver Generators", "40", "ACT-CIV-01", "0", "True"])
        writer.writerow(["ACT-ELE-GEN-INSTALL", "Install Generator", "20", "ACT-ELE-GEN-01", "0", "True"])
        writer.writerow(["ACT-ELE-UPS-INSTALL", "Install UPS", "20", "ACT-ELE-GEN-01", "10", "False"])
        writer.writerow(["ACT-COM-01", "Commissioning Stage 1", "15", "ACT-ELE-GEN-INSTALL", "0", "True"])
    print("Generated schedule.csv")
            
    # cx_test_register.csv
    cx_path = os.path.join(corpus_root, "registers", "cx_test_register.csv")
    with open(cx_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["test_id", "level", "system", "spec_clause", "acceptance_criteria", "status"])
        writer.writerow(["CX-263353-01", "L4", "Electrical", "26 33 53 Part 2.3.4", "Inverter efficiency shall be not less than 96.0 percent at full load.", "PENDING"])
        writer.writerow(["CX-263213-01", "L4", "Electrical", "26 32 13 Part 3.2.1.F", "Fuel day tank capacity shall be not less than 1200 litres.", "PENDING"])
    print("Generated cx_test_register.csv")
            
    # rfi_log.csv
    rfi_path = os.path.join(corpus_root, "registers", "rfi_log.csv")
    with open(rfi_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["rfi_id", "subject", "query", "response", "status"])
        writer.writerow(["RFI-001", "UPS Redundancy", "Is N+1 redundancy acceptable?", "Yes", "CLOSED"])
    print("Generated rfi_log.csv")

    print("\nTest corpus generation complete! Check the 'test_corpus' folder.")


if __name__ == "__main__":
    main()
