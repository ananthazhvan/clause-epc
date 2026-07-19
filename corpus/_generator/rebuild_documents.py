from pathlib import Path
import yaml,json,html,re,subprocess,hashlib,textwrap
from datetime import datetime
R=Path('/data/meridian_build/corpus')
B=yaml.safe_load((R/'bible/project_bible.yaml').read_text())

def esc(x): return html.escape(str(x))
def slug(s): return s.lower().replace(' ','_').replace('/','_')
CSS='''
@page{size:A4;margin:14mm 14mm 16mm 18mm;@bottom-left{content:"MER-1-2026 | IFC REV C";font:8pt Arial;color:#666}@bottom-right{content:"Page " counter(page) " of " counter(pages);font:8pt Arial;color:#666}}
*{box-sizing:border-box}html{background:#eceff1}body{margin:0;font:10pt/1.38 Arial,Helvetica,sans-serif;color:#1f252b;background:#eceff1}.sheet{width:210mm;min-height:297mm;margin:10mm auto;background:white;padding:15mm 15mm 18mm 19mm;position:relative;break-after:page;box-shadow:0 2px 14px #0002}.sheet:last-child{break-after:auto}.docbar{border-top:5px solid #1f4e79;border-bottom:1px solid #8ca3b8;padding:8px 0 7px;margin-bottom:16px;display:flex;justify-content:space-between;gap:12px;font-size:8.5pt;color:#40515f}.brand{font-weight:700;color:#1f4e79;letter-spacing:.04em}.section-no{font-size:12pt;letter-spacing:.12em;color:#4d5b66}.cover h1{font-size:24pt;line-height:1.12;color:#173f63;margin:32mm 0 8mm}.cover h2{font-size:17pt;font-weight:500;margin:0 0 25mm}.title-rule{height:7px;background:#1f4e79;width:68mm;margin-bottom:10mm}.meta{border-collapse:collapse;width:100%;font-size:9.5pt}.meta td{border:1px solid #9aa8b2;padding:7px}.meta td:first-child{width:36%;background:#eef3f6;font-weight:bold}.status{display:inline-block;border:2px solid #1f4e79;padding:6px 12px;color:#1f4e79;font-weight:bold;letter-spacing:.08em}.part{font-size:15pt;color:#173f63;border-bottom:2px solid #173f63;padding-bottom:5px;margin:0 0 13px}.clause{margin:0 0 13px}.clause h3{font-size:10.5pt;margin:0 0 4px;color:#172d3d}.clause p{margin:3px 0}.clause ol{margin:4px 0 4px 22px;padding:0}.clause li{margin:3px 0}.req{border-left:4px solid #2f6f9f;background:#f2f7fa;padding:8px 10px;margin:7px 0}.toc{width:100%;border-collapse:collapse}.toc td{padding:5px 3px;border-bottom:1px dotted #9ca8b0}.toc td:last-child{text-align:right}.schedule{width:100%;border-collapse:collapse;font-size:8.6pt;margin:8px 0}.schedule th{background:#dce7ef;color:#183b55;text-align:left}.schedule th,.schedule td{border:1px solid #94a6b3;padding:5px;vertical-align:top}.note{background:#fff7df;border-left:4px solid #d39b22;padding:8px 10px}.footer-note{position:absolute;bottom:10mm;left:19mm;right:15mm;border-top:1px solid #ccd3d8;padding-top:4px;color:#6a747c;font-size:7.5pt}.end{text-align:center;margin-top:90mm;font-weight:bold;letter-spacing:.12em}.vendor-head{border-bottom:4px solid var(--accent);padding-bottom:8px;margin-bottom:14px}.vendor-name{font-size:22pt;font-weight:bold;color:var(--accent)}.vendor-tag{font-size:8pt;letter-spacing:.12em;color:#59646c}.revision{border:2px solid var(--accent);color:var(--accent);font-weight:bold;padding:5px 9px;display:inline-block}.signature{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:18px}.signline{border-top:1px solid #555;padding-top:4px;font-size:8pt}.yes{color:#176b3a;font-weight:bold}.no{color:#a12622;font-weight:bold}.small{font-size:8pt;color:#5e686f}.page-title{font-size:16pt;color:var(--accent);margin:0 0 13px;border-bottom:2px solid var(--accent);padding-bottom:5px}
@media print{html,body{background:white}.sheet{margin:0;box-shadow:none;width:auto;min-height:0;height:267mm;padding:0;page-break-after:always}.sheet:last-child{page-break-after:auto}.footer-note{bottom:0;left:0;right:0}}
'''

def doc(head,body,accent='#1f4e79'):
 return f'<!doctype html><html><head><meta charset="utf-8"><style>:root{{--accent:{accent}}}{CSS}</style><title>{esc(head)}</title></head><body>{body}</body></html>'

def top(label,code='MER-1-2026'):
 return f'<div class="docbar"><span class="brand">MERIDIAN-1 DATA CENTRE — HALL A</span><span>{esc(label)} | {code}</span></div>'

def sheet(content,cls=''):
 return f'<section class="sheet {cls}">{content}<div class="footer-note">Controlled project document • Times and dates use Asia/Kolkata • Uncontrolled when printed</div></section>'

def requirement_text(r):
 p,v,rule=r['parameter'],r['value'],r['rule']
 if rule=='minimum': return f'{p} shall be not less than <b>{v}</b>.'
 if rule=='maximum': return f'{p} shall not exceed <b>{v}</b>.'
 return f'{p} shall be <b>{v}</b>.'

def section_specific(sec,title):
 n=sec.replace(' ','')
 refs={
 '212200':['NFPA 2001 (2022)','ISO 14520-1:2015','IS 2190:2010','CEA fire-safety requirements'],
 '232113':['ASME B31.9-2020','ASTM A106/A106M-2019a','IS 1239','IS 2062:2011'],
 '236426':['AHRI 550/590-2023','ASHRAE 90.1-2022','ISO 16358-1:2013','IS 16590'],
 '236500':['CTI ATC-105 (2019)','CTI STD-201 RS (2020)','IS 13095','ASHRAE 90.1-2022'],
 '230923':['BACnet ISO 16484-5:2022','ASHRAE Guideline 36-2021','IEC 61131-3:2013','IS/IEC 61000'],
 '255000':['BACnet ISO 16484-5:2022','IEC 61850','IEC 62443-3-3:2013','TIA-942-C'],
 '260526':['IS 3043:2018','IEC 60364-5-54:2011','IEEE 80-2013','CEA Safety Regulations 2023'],
 '262413':['IEC 61439-1:2020','IEC 61439-2:2020','IS/IEC 60947','IS 8623'],
 '263213':['ISO 8528-1:2018','ISO 3046-1:2002','CPCB IV+ norms','IS 4722:2001'],
 '263353':['IEC 62040-1:2017','IEC 62040-2:2016','IEC 62040-3:2021','TIA-942-C'],
 '271500':['ISO/IEC 11801-1:2017','TIA-568.2-D','TIA-568.3-E','IEC 60332'],
 '283111':['IS 2189:2008','NFPA 72-2022','EN 54','NBC India 2016 Part 4']}
 comps={
 '212200':['agent storage cylinders','selector and discharge valves','distribution pipework and nozzles','releasing control panel','abort/manual-release stations'],
 '232113':['seamless carbon-steel pipe','butt-weld fittings and flanges','isolation and balancing valves','strainers and flexible connectors','supports, guides and anchors'],
 '236426':['compressor and drive','flooded evaporator','water-cooled condenser','microprocessor control panel','refrigerant and oil systems'],
 '236500':['FRP casing and basin','fill and drift eliminators','axial fans and drives','make-up and blowdown assemblies','vibration and acoustic controls'],
 '230923':['native BACnet controllers','I/O modules','temperature and pressure sensors','control panels and power supplies','operator and engineering tools'],
 '255000':['integration servers','BACnet and Modbus gateways','EPMS data concentrators','historian and alarm services','cybersecurity and time synchronisation'],
 '260526':['buried copper grid','equipment bonding conductors','earth electrodes and inspection pits','test links and bars','equipotential bonding network'],
 '262413':['withdrawable ACB incomers','form 4b busbar chambers','MCCB outgoing feeders','metering and protection relays','arc containment and interlocks'],
 '263213':['diesel engine','alternator and AVR','base frame and radiator','day tank and fuel controls','synchronising and generator controller'],
 '263353':['rectifier and inverter modules','static bypass','maintenance bypass','battery strings and breakers','monitoring and communication cards'],
 '271500':['Category 6A horizontal cable','modular jacks and patch panels','OS2 optical-fibre cable','fibre enclosures and pigtails','racks, pathways and labels'],
 '283111':['addressable fire-alarm panel','detector and module loops','smoke and heat detectors','sounder-strobes and interfaces','network and graphics workstation']}
 return refs[n],comps[n]

# Rebuild 12 CSI specifications with relevant clauses only.
for sec in B['sections']:
 s,t=sec['number'],sec['title']; refs,comps=section_specific(s,t); reqs=sec['requirements']; pages=[]
 pages.append(sheet(top(f'SECTION {s}')+f'<div class="cover"><div class="section-no">SECTION {s}</div><h1>{esc(t).upper()}</h1><div class="title-rule"></div><h2>TECHNICAL SPECIFICATION</h2><table class="meta"><tr><td>Project</td><td>MERIDIAN-1 Data Centre, Hall A</td></tr><tr><td>Project code</td><td>MER-1-2026</td></tr><tr><td>Issue</td><td>Issued for Construction — Revision C</td></tr><tr><td>Issue date</td><td>17 February 2026</td></tr><tr><td>Electrical basis</td><td>11 kV / 415 V, 3-phase, 50 Hz</td></tr></table></div>','cover'))
 toc=['PART 1 — GENERAL','1.1 Summary','1.2 References','1.3 Definitions','1.4 Submittals','1.5 Quality assurance','1.6 Delivery, storage and handling','PART 2 — PRODUCTS','2.1 System description','2.2 Manufactured units','2.3 Components','2.4 Performance requirements','2.5 Controls and interfaces','2.6 Source quality control','2.7 Test standards','PART 3 — EXECUTION','3.1 Examination','3.2 Installation','3.3 Field quality control','3.4 Performance verification','3.5 Commissioning','3.6 Training and closeout']
 pages.append(sheet(top(f'SECTION {s}')+'<h2 class="part">TABLE OF CONTENTS</h2><table class="toc">'+''.join(f'<tr><td>{esc(x)}</td><td>{2+i//2}</td></tr>' for i,x in enumerate(toc))+'</table>'))
 p1=f'''{top(f'SECTION {s}')}<h2 class="part">PART 1 — GENERAL</h2><div class="clause"><h3>1.1 SUMMARY</h3><p>A. Provide complete {esc(t.lower())} for Hall A, including engineering, manufacture, delivery, installation support, testing, commissioning and training.</p><p>B. Coordinate equipment clearances, structural loads, electrical supplies, controls interfaces, fire strategy, maintainability and phased energisation.</p><p>C. Related work includes sections 23 09 23, 25 50 00, 26 05 26 and the project commissioning requirements.</p></div><div class="clause"><h3>1.2 REFERENCES</h3><ol type="A">{''.join(f'<li>{esc(r)}</li>' for r in refs)}</ol><p>Use the editions stated unless a later statutory edition is mandatory in India. Where requirements conflict, apply the more stringent requirement and raise an RFI.</p></div><div class="clause"><h3>1.3 DEFINITIONS</h3><p>A. “Approved” means accepted for the stated stage without relieving the Contractor of performance responsibility.</p><p>B. “Provide” means design, supply, install, connect, test, commission and document.</p></div>'''
 pages.append(sheet(p1))
 p1b=f'''{top(f'SECTION {s}')}<h2 class="part">PART 1 — GENERAL — CONTINUED</h2><div class="clause"><h3>1.4 SUBMITTALS</h3><ol type="A"><li>Product data with model, rating, dimensions, weight, service clearances and scheduled duty.</li><li>Clause-by-clause compliance matrix identifying exceptions without qualification.</li><li>Certified performance curves and selection calculations at the specified site conditions.</li><li>Type-test certificates traceable to the offered construction and current test standard.</li><li>Factory inspection and test plan identifying hold, witness and review points.</li><li>Interface schedule for power, controls, alarms, network, drainage and builder’s work.</li><li>Operation and maintenance information, recommended spares and training plan.</li></ol></div><div class="clause"><h3>1.5 QUALITY ASSURANCE</h3><p>A. Manufacturer shall operate an ISO 9001-certified quality system and demonstrate at least five years’ experience with comparable data-centre duty.</p><p>B. Calibrations shall be traceable to NABL-accredited or mutually recognised laboratories.</p></div><div class="clause"><h3>1.6 DELIVERY, STORAGE AND HANDLING</h3><p>Protect equipment from moisture, shock, corrosion and contamination. Record preservation checks monthly. Maintain tag, PO, serial-number and material-heat traceability through installation.</p></div>'''
 pages.append(sheet(p1b))
 # Part 2 across four pages, each requirement only at its real clause
 groups=[('2.1 SYSTEM DESCRIPTION',comps[:2],reqs[:1]),('2.2 MANUFACTURED UNITS',comps[2:4],reqs[1:2]),('2.3 COMPONENTS AND ACCESSORIES',comps,reqs[2:3]),('2.4 PERFORMANCE AND CONTROLS',comps[3:],reqs[3:])]
 for title,items,rq in groups:
  content=top(f'SECTION {s}')+f'<h2 class="part">PART 2 — PRODUCTS</h2><div class="clause"><h3>{title}</h3><p>A. Furnish a coordinated, factory-engineered assembly rated for continuous operation at 40 °C ambient unless a more severe condition is scheduled.</p><ol type="A">'+''.join(f'<li><b>{esc(x).title()}:</b> construction, rating and interfaces shall be documented in the approved technical schedule.</li>' for x in items)+'</ol></div>'
  for r in rq: content+=f'<div class="req"><b>{s} {r["clause"]}</b> — {requirement_text(r)}</div>'
  content+=f'''<div class="clause"><h3>{title.split()[0]}.9 IDENTIFICATION AND MAINTAINABILITY</h3><p>Provide engraved equipment identification, durable terminal references, isolation labels and QR-linked asset data. Components requiring routine service shall be replaceable without disturbing adjacent live systems.</p></div><div class="clause"><h3>{title.split()[0]}.10 ENVIRONMENTAL CONDITIONS</h3><p>Equipment shall withstand transport and storage from 5 °C to 50 °C and operation at the scheduled indoor or outdoor condition, 95 percent non-condensing relative humidity, and the project seismic restraint basis.</p></div>'''
  pages.append(sheet(content))
 p2=f'''{top(f'SECTION {s}')}<h2 class="part">PART 2 — PRODUCTS — CONTINUED</h2><div class="clause"><h3>2.5 CONTROLS AND INTERFACES</h3><p>A. Hardwired safety and shutdown functions shall not depend solely on the BMS network.</p><p>B. Provide BACnet/IP or Modbus TCP points as scheduled, including status, alarm, command, measurement, setpoint and maintenance counters.</p><p>C. All timestamps shall synchronise to the project NTP service in Asia/Kolkata.</p></div><div class="clause"><h3>2.6 SOURCE QUALITY CONTROL</h3><p>Perform documented incoming inspection, in-process checks, torque verification, insulation checks, functional simulation and final inspection. Record calibrated instrument serial numbers and as-left settings.</p></div><div class="clause"><h3>2.7 TEST STANDARDS</h3><p>Apply the listed reference standards at the stated duty and environmental condition. A test conducted on a materially different rating, construction or operating condition is not automatically representative.</p></div>'''
 pages.append(sheet(p2))
 # Part 3 three pages
 for h,paras in [('3.1 EXAMINATION AND INSTALLATION',['Verify foundations, access routes, service clearances and embedded services before installation.','Install level, plumb, aligned and restrained. Use calibrated torque tools and record critical fastener values.','Coordinate penetrations, sleeves, fire stopping, earthing, controls and identification.']),('3.3 FIELD QUALITY CONTROL',['Inspect installation against approved drawings and manufacturer instructions.','Test continuity, insulation, pressure, leakage, rotation, interlocks and alarms as applicable.','Record deficiencies in ACC and close them before functional performance testing.']),('3.4 PERFORMANCE VERIFICATION AND COMMISSIONING',['Execute L2 site acceptance, L3 pre-functional, L4 functional performance and L5 integrated systems tests.','Trend operating values during stable load and compare each measured result with its acceptance criterion.','Submit signed test records, calibrated instrument certificates, final settings, training attendance and O&M data.'])]:
  c=top(f'SECTION {s}')+f'<h2 class="part">PART 3 — EXECUTION</h2><div class="clause"><h3>{h}</h3><ol type="A">'+''.join(f'<li>{esc(x)}</li>' for x in paras)+'</ol></div>'
  if h.startswith('3.4'):
   for r in reqs: c+=f'<div class="req"><b>Acceptance — {s} {r["clause"]}</b>: {requirement_text(r)}</div>'
  c+='<div class="clause"><h3>3.6 TRAINING AND CLOSEOUT</h3><p>Train operations personnel using the installed equipment. Demonstrate normal operation, changeover, alarm response, isolation, emergency action, preventive maintenance and safe return to service.</p></div>'
  pages.append(sheet(c))
 pages.append(sheet(top(f'SECTION {s}')+f'<div class="end">END OF SECTION {s}</div>'))
 out=R/'specs'/f'{s.replace(" ","")}_{slug(t)}.html'; out.write_text(doc(f'{s} {t}', ''.join(pages)))

# Convert generic discrepancy phrases to realistic submitted statements.
def realistic(q):
 p=q['parameter']; raw=q['submitted']; spec=q['spec_value']
 explicit={
 'Cylinder working pressure':{'below requirement':'40 bar at 20 °C'},'Discharge duration':{'above requirement':'12.4 s'},
 'Pipe material':{'nonmatching value':'ASTM A53 Grade B ERW'},'Design pressure':{'below requirement':'14 bar'},
 'Full-load COP':{'below requirement':'6.0'},'Evaporator pressure drop':{'above requirement':'103 kPa'},
 'Thermal capacity':{'below requirement':'4,280 kW'},'Sound pressure at 1 m':{'above requirement':'86 dBA at 1 m'},
 'Rated operational voltage':{'nonmatching value':'400 V'},'Short-circuit withstand':{'below requirement':'50 kA for 1 s'},
 'Rated output':{'below requirement':'1,800 kVA'},'Battery autonomy':{'below requirement':'12 minutes at 1,600 kW'},
 'Prime power rating':{'below requirement':'2,250 kVA at 0.8 pf'},'Loop capacity':{'below requirement':'200 devices'},
 'Controller scan cycle':{'above requirement':'2.5 s'},'Temperature sensor accuracy':{'above requirement':'±0.30 °C'}}
 if raw in explicit.get(p,{}): return explicit[p][raw]
 return raw

vendors={v['name']:v for v in B['vendors']}
for p in B['packages']:
 v=vendors[p['vendor']]; accent=v['accent']; sec=next(s for s in B['sections'] if s['number']==p['section']); reqs=sec['requirements']; cases=[x for x in B['quality_cases'] if x['package']==p['id']]; good=[x for x in B['conforming_examples'] if x['package']==p['id']]; rev=p['id'].split('-')[-1]
 def vh(title): return top(p['id'])+f'<div class="vendor-head"><div class="vendor-name">{esc(v["name"])}</div><div class="vendor-tag">{esc(v["voice"]).upper()} • SAP {v["sap"]}</div></div><h1 class="page-title">{title}</h1>'
 pages=[]
 pages.append(sheet(vh('Technical Submittal')+f'<div style="margin-top:25mm"><div class="revision">{rev} — FOR TECHNICAL REVIEW</div><h2 style="font-size:22pt;margin:12mm 0 5mm">{esc(p["scope"])}</h2><table class="meta"><tr><td>Package ID</td><td>{p["id"]}</td></tr><tr><td>Reference Section</td><td>{p["section"]}</td></tr><tr><td>Reviewed Spec Revision</td><td>Rev C{", including ADD-001" if p["section"] in ["23 64 26","26 33 53"] else ", including ADD-002" if p["section"] in ["23 65 00","27 15 00"] else ""}</td></tr><tr><td>Project</td><td>MERIDIAN-1 Data Centre, Hall A</td></tr><tr><td>Submitted</td><td>{"2026-04-14" if rev=="R1" else "2026-03-18"}</td></tr></table></div>'))
 pages.append(sheet(vh('Transmittal and Document Register')+'<table class="schedule"><tr><th>No.</th><th>Document</th><th>Document reference</th><th>Rev.</th><th>Purpose</th></tr>'+''.join(f'<tr><td>{i}</td><td>{x}</td><td>{p["id"]}-{i:02d}</td><td>{rev}</td><td>Technical review</td></tr>' for i,x in enumerate(['Technical schedule','Compliance statement','Certified performance data','Type-test evidence','Material traceability','Inspection and test plan'],1))+'</table><div class="note"><b>Revision note:</b> '+('Resubmission superseding R0. Review comments and applicable addendum requirements have been incorporated.' if rev=='R1' else 'Initial submission. Any departure is identified in the compliance schedule and shall not be inferred from catalogue data.')+'</div>'))
 # datasheet
 data_rows=''.join(f'<tr><td>{r["clause"]}</td><td>{esc(r["parameter"])}</td><td>{esc(r["value"])}</td><td>{esc(realistic(cases[i]) if i<len(cases) else r["value"])}</td></tr>' for i,r in enumerate(reqs))
 pages.append(sheet(vh('Equipment Technical Schedule')+f'<table class="schedule"><tr><th>Clause</th><th>Scheduled parameter</th><th>Specified</th><th>Offered</th></tr>{data_rows}</table><h3>Design conditions</h3><table class="schedule"><tr><td>Electrical supply</td><td>415 V, 3-phase, 50 Hz unless scheduled otherwise</td></tr><tr><td>Site</td><td>Navi Mumbai, India</td></tr><tr><td>Maximum ambient</td><td>40 °C indoor design basis</td></tr><tr><td>Controls</td><td>Hardwired safety; BACnet/IP or Modbus TCP supervisory interface</td></tr></table><p class="small">Selections are project-specific. Catalogue ratings at other conditions are not substituted for scheduled duty.</p>'))
 # compliance matrix only once
 rows=''
 for r in reqs:
  qs=[q for q in cases if q['clause']==r['clause']]
  val=realistic(qs[0]) if qs else r['value']; status='EXCEPTION' if qs else 'COMPLIES'; cls='no' if qs else 'yes'
  rows+=f'<tr><td>{r["clause"]}</td><td>{requirement_text(r)}</td><td>{esc(val)}</td><td class="{cls}">{status}</td></tr>'
 pages.append(sheet(vh('Clause-by-Clause Compliance Statement')+f'<table class="schedule"><tr><th>Clause</th><th>Requirement</th><th>Submitted basis</th><th>Status</th></tr>{rows}</table><div class="note">Status is based on the evidence in this package. “Complies” does not waive specified witness testing.</div>'))
 # cert page includes case evidence and narrative arcs
 evid=''.join(f'<tr><td>{q["clause"]}</td><td>{esc(q["parameter"])}</td><td>{esc(realistic(q))}</td><td>{esc(q["source"])}</td></tr>' for q in cases) or '<tr><td colspan="4">No qualification recorded in this evidence schedule.</td></tr>'
 arc=''
 if p['id']=='SUB-212200-01-R0': arc='<div class="note"><b>Certificate observation:</b> Cylinder certificate AF-CYL-24017 records 40 bar at 20 °C; the technical schedule identifies 42 bar.</div>'
 if p['id']=='SUB-262413-01-R0': arc='<div class="note"><b>Type-test scope:</b> Certificate MS-IEC-61439-22 records 50 kA for 1 s for the tested assembly.</div>'
 if p['id']=='SUB-263353-01-R0': arc='<div class="note"><b>Test condition:</b> Published efficiency is at unity power factor. The 0.9-lagging witness point remains open.</div>'
 pages.append(sheet(vh('Type-Test and Performance Evidence')+f'<table class="schedule"><tr><th>Clause</th><th>Characteristic</th><th>Evidence statement</th><th>Record</th></tr>{evid}</table>{arc}<h3>Evidence controls</h3><p>Certificates shall identify laboratory, standard edition, test object, rating, construction, date and authorised signatory. Similarity claims require an engineering comparison.</p>'))
 trace='<p>Material and component records are indexed by equipment tag, purchase order, serial number and source lot.</p><table class="schedule"><tr><th>Item</th><th>Trace reference</th><th>Inspection</th></tr><tr><td>Primary assembly</td><td>'+p['id']+'-MTR-01</td><td>Incoming inspection accepted</td></tr><tr><td>Safety-critical components</td><td>'+p['id']+'-SCC-01</td><td>Certificate review required</td></tr><tr><td>Labels and terminals</td><td>'+p['id']+'-ID-01</td><td>100% visual check</td></tr></table>'
 if p['id']=='SUB-232113-01-R0': trace+='<div class="note"><b>Mill certificate:</b> Pipe lot CHW-P-044 cites heat TF-HN-7782.</div>'
 pages.append(sheet(vh('Material and Component Traceability')+trace))
 itp='<table class="schedule"><tr><th>Seq.</th><th>Inspection / test</th><th>Acceptance</th><th>Point</th><th>Record</th></tr><tr><td>10</td><td>Document and drawing review</td><td>Approved data</td><td>R</td><td>Review sheet</td></tr><tr><td>20</td><td>Incoming material inspection</td><td>Approved BOM and certificates</td><td>W</td><td>Material report</td></tr><tr><td>30</td><td>Assembly and workmanship</td><td>Approved drawings</td><td>S</td><td>Inspection checklist</td></tr><tr><td>40</td><td>Rated functional test</td><td>Section '+p['section']+'</td><td>H</td><td>FAT record</td></tr><tr><td>50</td><td>Final inspection and release</td><td>No open major NCR</td><td>W</td><td>Release note</td></tr></table><p class="small">H = hold, W = witness, R = review, S = surveillance. Give seven calendar days’ notice for witness and hold points.</p>'
 pages.append(sheet(vh('Factory Inspection and Test Plan')+itp))
 pages.append(sheet(vh('Exceptions, Declarations and Sign-Off')+'<h3>Declared exceptions</h3><p>'+('Exceptions are identified in the compliance statement and require Engineer disposition before release for manufacture.' if cases else 'No exceptions declared against the reviewed specification revision.')+'</p><h3>Manufacturer declaration</h3><p>We certify that this package is prepared for MER-1-2026 and that the offered construction will not be changed without formal resubmission.</p><div class="signature"><div class="signline">Prepared by: Package Engineer</div><div class="signline">Approved by: Engineering Manager</div><div class="signline">Date: '+('14 April 2026' if rev=='R1' else '18 March 2026')+'</div><div class="signline">Document status: Technical review</div></div>'))
 (R/'submittals'/f'{p["id"]}.html').write_text(doc(p['id'],''.join(pages),accent))

# Update evaluation submitted values to match realistic rendered evidence.
v=json.loads((R/'answer_key/violations_key.json').read_text())
for item,q in zip(v,B['quality_cases']): item['submitted_value']=realistic(q)
(R/'answer_key/violations_key.json').write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
# Render HTML directly with Chromium; PDF visual is therefore identical to print CSS.
for folder in ['specs','submittals','addenda']:
 for hp in sorted((R/folder).glob('*.html')):
  out=hp.with_suffix('.pdf')
  subprocess.run(['chromium','--headless','--no-sandbox','--disable-gpu','--run-all-compositor-stages-before-draw','--no-pdf-header-footer','--print-to-pdf='+str(out),hp.as_uri()],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
# Refresh manifest after all writes.
items=[]
for p in sorted(R.rglob('*')):
 if p.is_file() and p.name not in ['manifest.sha256','build.log']:
  items.append(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(R)}')
(R/'manifest.sha256').write_text('\n'.join(items)+'\n')
print('Rebuilt',len(list((R/'specs').glob('*.html'))),'specifications and',len(list((R/'submittals').glob('*.html'))),'submittals')
