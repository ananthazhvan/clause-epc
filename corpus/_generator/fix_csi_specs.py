from pathlib import Path
import yaml,html,re,subprocess,hashlib
R=Path(__file__).resolve().parents[1]
B=yaml.safe_load((R/'bible/project_bible.yaml').read_text())

def e(x): return html.escape(str(x))
def slug(s): return s.lower().replace(' ','_').replace('/','_')
CSS='''@page{size:A4;margin:14mm 15mm 16mm 18mm}*{box-sizing:border-box}html{background:#e9edef}body{margin:0;background:#e9edef;color:#20262b;font:10pt/1.38 Arial,sans-serif}.sheet{width:210mm;min-height:297mm;margin:9mm auto;padding:15mm 15mm 18mm 19mm;background:#fff;position:relative;break-after:page;box-shadow:0 2px 12px #0002}.sheet:last-child{break-after:auto}.head{border-top:5px solid #174a72;border-bottom:1px solid #8ca0ae;padding:7px 0;margin-bottom:15px;display:flex;justify-content:space-between;font-size:8pt;color:#314857}.head b{color:#174a72;letter-spacing:.05em}.part{font-size:16pt;color:#173f63;border-bottom:3px solid #173f63;padding-bottom:5px;margin:0 0 14px}.article{font-size:11pt;color:#1e3342;margin:15px 0 6px}.alpha{list-style-type:upper-alpha;margin:0 0 8px 24px;padding:0}.alpha>li{padding-left:4px;margin:5px 0}.num{list-style-type:decimal;margin:5px 0 5px 22px}.num>li{margin:3px 0}.lower{list-style-type:lower-alpha;margin:3px 0 3px 20px}.footer{position:absolute;left:19mm;right:15mm;bottom:9mm;border-top:1px solid #c5cdd2;padding-top:4px;font-size:7.5pt;color:#66717a}.cover h1{font-size:23pt;color:#173f63;margin:37mm 0 7mm;line-height:1.12}.cover h2{font-size:16pt;font-weight:400;margin-top:12mm}.rule{height:6px;background:#174a72;width:65mm}.meta{border-collapse:collapse;width:100%;margin-top:24mm}.meta td{border:1px solid #94a4af;padding:7px}.meta td:first-child{width:35%;font-weight:bold;background:#edf2f5}.contents{width:100%;border-collapse:collapse}.contents td{padding:5px;border-bottom:1px dotted #9aa4aa}.contents .p{font-weight:bold;background:#edf2f5;color:#173f63}.section-title{letter-spacing:.14em;color:#566773}.end{text-align:center;margin-top:105mm;font-weight:bold;letter-spacing:.15em}.req{font-weight:normal}.req b{font-weight:700}.small{font-size:8pt;color:#5d6870}@media print{html,body{background:#fff}.sheet{width:auto;height:267mm;min-height:0;margin:0;padding:0;box-shadow:none;page-break-after:always}.sheet:last-child{page-break-after:auto}.footer{left:0;right:0;bottom:0}}'''

def head(s): return f'<div class="head"><b>MERIDIAN-1 DATA CENTRE — HALL A</b><span>SECTION {s} | MER-1-2026</span></div>'
def page(s,body,cls=''): return f'<section class="sheet {cls}">{head(s)}{body}<div class="footer">SECTION {s} • Issued for Construction • Revision C • Uncontrolled when printed</div></section>'
def requirement(r):
 if r['rule']=='minimum': return f'{e(r["parameter"])} shall be not less than <b>{e(r["value"])}</b>.'
 if r['rule']=='maximum': return f'{e(r["parameter"])} shall not exceed <b>{e(r["value"])}</b>.'
 return f'{e(r["parameter"])} shall be <b>{e(r["value"])}</b>.'

def article(s,num,title,reqs,base,details=None):
 byletter={r['clause'].split('.')[-1]:r for r in reqs if r['clause'].rsplit('.',1)[0]==num}
 maxletter=max([ord(x)-64 for x in byletter] or [len(base)])
 count=max(len(base),maxletter)
 lis=[]
 for i in range(1,count+1):
  L=chr(64+i)
  if L in byletter: text=requirement(byletter[L]); cls=' class="req"'
  else: text=base[i-1] if i<=len(base) else f'Provide documented evidence demonstrating compliance with the requirements of this Article.'; cls=''
  nested=''
  if details and i==1: nested='<ol class="num">'+''.join(f'<li>{e(x)}</li>' for x in details)+'</ol>'
  lis.append(f'<li{cls}>{text}{nested}</li>')
 return f'<h3 class="article">{num} {e(title)}</h3><ol class="alpha">{"".join(lis)}</ol>'

components={
'21 22 00':['Agent storage cylinders and valve assemblies','Distribution piping and discharge nozzles','Releasing control panel and abort/manual-release devices'],
'23 21 13':['Carbon-steel chilled-water piping','Fittings, flanges, valves and strainers','Supports, anchors, guides and flexible connectors'],
'23 64 26':['Compressor and variable-speed drive','Evaporator and water-cooled condenser','Controls, safeties and refrigerant circuits'],
'23 65 00':['FRP casing, basin, fill and drift eliminators','Axial fans, motors and transmission','Make-up, blowdown, vibration and acoustic controls'],
'23 09 23':['Native BACnet DDC controllers','I/O modules, sensors and actuators','Control panels, power supplies and engineering tools'],
'25 50 00':['Integration servers and gateways','EPMS data concentrators and historian','Cybersecurity, alarm and time-synchronisation services'],
'26 05 26':['Buried copper grid and electrodes','Equipment bonding conductors and test links','Earth bars, pits and equipotential bonds'],
'26 24 13':['Withdrawable ACB incomers and bus couplers','Form 4b busbars and outgoing feeders','Protection, metering, interlocks and arc containment'],
'26 32 13':['Diesel engine and cooling system','Alternator, AVR and generator controller','Base frame, fuel system and synchronising controls'],
'26 33 53':['Rectifier and inverter power modules','Static bypass and maintenance bypass','Battery strings, breakers and monitoring cards'],
'27 15 00':['Category 6A horizontal cabling and connectivity','OS2 optical-fibre backbone and enclosures','Racks, pathways, patching and administration'],
'28 31 11':['Addressable fire-alarm control panels','Detection, notification and interface devices','Network, graphics and cause-and-effect controls']}
refs={
'21 22 00':['NFPA 2001 (2022)','ISO 14520-1:2015','IS 2190:2010'], '23 21 13':['ASME B31.9-2020','ASTM A106/A106M-2019a','IS 1239'], '23 64 26':['AHRI 550/590-2023','ASHRAE 90.1-2022','ISO 16358-1:2013'], '23 65 00':['CTI ATC-105 (2019)','CTI STD-201 RS (2020)','IS 13095'], '23 09 23':['ISO 16484-5:2022','ASHRAE Guideline 36-2021','IEC 61131-3:2013'], '25 50 00':['ISO 16484-5:2022','IEC 61850','IEC 62443-3-3:2013'], '26 05 26':['IS 3043:2018','IEC 60364-5-54:2011','IEEE 80-2013'], '26 24 13':['IEC 61439-1:2020','IEC 61439-2:2020','IS/IEC 60947'], '26 32 13':['ISO 8528-1:2018','ISO 3046-1:2002','CPCB IV+'], '26 33 53':['IEC 62040-1:2017','IEC 62040-2:2016','IEC 62040-3:2021'], '27 15 00':['ISO/IEC 11801-1:2017','TIA-568.2-D','TIA-568.3-E'], '28 31 11':['IS 2189:2008','NFPA 72-2022','EN 54']}
articles=[('1.1','SUMMARY'),('1.2','REFERENCES'),('1.3','DEFINITIONS'),('1.4','ACTION SUBMITTALS'),('1.5','INFORMATIONAL SUBMITTALS'),('1.6','CLOSEOUT SUBMITTALS'),('1.7','QUALITY ASSURANCE'),('1.8','DELIVERY, STORAGE, AND HANDLING'),('1.9','WARRANTY'),('2.1','MANUFACTURERS'),('2.2','PERFORMANCE REQUIREMENTS'),('2.3','EQUIPMENT'),('2.4','COMPONENTS'),('2.5','CONTROLS AND INTERFACES'),('2.6','SOURCE QUALITY CONTROL'),('2.7','FACTORY TESTING'),('3.1','EXAMINATION'),('3.2','INSTALLATION'),('3.3','FIELD QUALITY CONTROL'),('3.4','PERFORMANCE VERIFICATION'),('3.5','COMMISSIONING'),('3.6','TRAINING AND CLOSEOUT')]
for sec in B['sections']:
 s,t,reqs=sec['number'],sec['title'],sec['requirements']; pages=[]
 pages.append(page(s,f'<div class="cover"><div class="section-title">SECTION {s}</div><h1>{e(t).upper()}</h1><div class="rule"></div><h2>TECHNICAL SPECIFICATION</h2><table class="meta"><tr><td>Project</td><td>MERIDIAN-1 Data Centre, Hall A</td></tr><tr><td>Project code</td><td>MER-1-2026</td></tr><tr><td>Issue</td><td>Issued for Construction — Revision C</td></tr><tr><td>Date</td><td>17 February 2026</td></tr></table></div>','cover'))
 rows=''.join(f'<tr class="{"p" if x.endswith(("GENERAL","PRODUCTS","EXECUTION")) else ""}"><td>{x}</td></tr>' for x in ['PART 1 — GENERAL','1.1 Summary','1.2 References','1.3 Definitions','1.4 Action Submittals','1.5 Informational Submittals','1.6 Closeout Submittals','1.7 Quality Assurance','1.8 Delivery, Storage, and Handling','1.9 Warranty','PART 2 — PRODUCTS','2.1 Manufacturers','2.2 Performance Requirements','2.3 Equipment','2.4 Components','2.5 Controls and Interfaces','2.6 Source Quality Control','2.7 Factory Testing','PART 3 — EXECUTION','3.1 Examination','3.2 Installation','3.3 Field Quality Control','3.4 Performance Verification','3.5 Commissioning','3.6 Training and Closeout'])
 pages.append(page(s,f'<h2 class="part">TABLE OF CONTENTS</h2><table class="contents">{rows}</table>'))
 p1=article(s,'1.1','SUMMARY',reqs,['Provide a complete, coordinated system including engineering, manufacture, delivery, installation support, testing, commissioning, training, and closeout.','Coordinate clearances, structural loads, electrical supplies, controls, fire strategy, access, and phased energisation.'])+article(s,'1.2','REFERENCES',reqs,['Comply with the following referenced standards.'],refs[s])+article(s,'1.3','DEFINITIONS',reqs,['“Approved” means accepted for the stated stage without relieving the Contractor of responsibility.','“Provide” means design, supply, install, connect, test, commission, and document.'])
 pages.append(page(s,'<h2 class="part">PART 1 — GENERAL</h2>'+p1))
 p1b=article(s,'1.4','ACTION SUBMITTALS',reqs,['Submit project-specific product data, selected ratings, dimensions, weights, clearances, and connection requirements.','Submit a clause-by-clause compliance statement identifying every exception.','Submit certified calculations and performance data at scheduled conditions.'])+article(s,'1.5','INFORMATIONAL SUBMITTALS',reqs,['Submit type-test certificates traceable to the offered construction.','Submit quality certificates, calibration records, and proposed factory inspection and test plan.'])+article(s,'1.6','CLOSEOUT SUBMITTALS',reqs,['Submit approved as-built data, final settings, test records, recommended spares, and operation and maintenance manuals.'])
 pages.append(page(s,'<h2 class="part">PART 1 — GENERAL</h2>'+p1b))
 p1c=article(s,'1.7','QUALITY ASSURANCE',reqs,['Manufacturer shall maintain an ISO 9001-certified quality system and demonstrate comparable data-centre experience.','Test instruments shall have current calibration traceable to a recognised laboratory.'])+article(s,'1.8','DELIVERY, STORAGE, AND HANDLING',reqs,['Protect equipment from moisture, shock, corrosion, and contamination.','Maintain equipment-tag, purchase-order, serial-number, and source-lot traceability.'])+article(s,'1.9','WARRANTY',reqs,['Provide the project warranty commencing at Taking Over or the date stated in the Contract, whichever governs.'])
 pages.append(page(s,'<h2 class="part">PART 1 — GENERAL</h2>'+p1c))
 # Products: requirements are inserted only at their exact article and paragraph letter.
 prod_base={
 '2.1':['Subject to compliance with the Contract Documents, provide the system by an approved manufacturer.','Products shall be current production models with local technical support in India.'],
 '2.2':['Equipment shall operate continuously at the scheduled duty and site conditions.','Selections shall include stated tolerances, fouling allowances, harmonics, diversity, and redundancy as applicable.','Published catalogue values shall not replace project-condition certified data.'],
 '2.3':['Provide a complete factory-engineered assembly with coordinated ratings and interfaces.','Materials shall be suitable for the operating environment and expected service life.'],
 '2.4':['Components shall be accessible for inspection, isolation, removal, and replacement.','Safety-critical devices shall be independently identified and fail to a safe state.','Internal wiring, terminals, piping, and accessories shall be permanently identified.'],
 '2.5':['Hardwired safety and shutdown functions shall not depend solely on the supervisory network.','Provide scheduled BACnet/IP or Modbus TCP status, alarm, command, measurement, and setpoint objects.','Synchronise event timestamps to the project NTP service in Asia/Kolkata.'],
 '2.6':['Perform documented incoming inspection, in-process checks, and final inspection.','Record material traceability, calibrated instrument numbers, torque values, and as-left settings.'],
 '2.7':['Submit the factory test procedure before testing.','Test the offered rating and construction at the specified operating condition.','Record raw measurements, calculated results, instrument details, and acceptance status.','Do not claim equivalence for a different rating or condition without an approved engineering comparison.']}
 pages.append(page(s,'<h2 class="part">PART 2 — PRODUCTS</h2>'+article(s,'2.1','MANUFACTURERS',reqs,prod_base['2.1'])+article(s,'2.2','PERFORMANCE REQUIREMENTS',reqs,prod_base['2.2'])))
 pages.append(page(s,'<h2 class="part">PART 2 — PRODUCTS</h2>'+article(s,'2.3','EQUIPMENT',reqs,prod_base['2.3'],components[s])+article(s,'2.4','COMPONENTS',reqs,prod_base['2.4'])))
 pages.append(page(s,'<h2 class="part">PART 2 — PRODUCTS</h2>'+article(s,'2.5','CONTROLS AND INTERFACES',reqs,prod_base['2.5'])+article(s,'2.6','SOURCE QUALITY CONTROL',reqs,prod_base['2.6'])))
 pages.append(page(s,'<h2 class="part">PART 2 — PRODUCTS</h2>'+article(s,'2.7','FACTORY TESTING',reqs,prod_base['2.7'])))
 exec_base={
 '3.1':['Verify foundations, access routes, clearances, environmental conditions, and embedded services before installation.','Do not proceed until unsatisfactory conditions are corrected.'],
 '3.2':['Install in accordance with approved drawings and manufacturer instructions.','Install level, aligned, restrained, labelled, and accessible for operation and maintenance.','Coordinate earthing, power, controls, penetrations, fire stopping, drainage, and builder’s work.'],
 '3.3':['Inspect the completed installation and record deficiencies.','Perform applicable continuity, insulation, pressure, leakage, rotation, interlock, and alarm tests.','Close major deficiencies before functional performance testing.'],
 '3.4':['Demonstrate each specified performance criterion at stable scheduled conditions.','Record measured values, instrument uncertainty, acceptance limits, and status.'],
 '3.5':['Execute L2 site acceptance, L3 pre-functional, L4 functional performance, and L5 integrated systems testing.','Coordinate test prerequisites, witnesses, temporary loads, trend logs, and restoration.'],
 '3.6':['Train operations personnel using the installed equipment.','Submit signed test records, final settings, training attendance, and approved closeout documents.']}
 pages.append(page(s,'<h2 class="part">PART 3 — EXECUTION</h2>'+article(s,'3.1','EXAMINATION',reqs,exec_base['3.1'])+article(s,'3.2','INSTALLATION',reqs,exec_base['3.2'])))
 pages.append(page(s,'<h2 class="part">PART 3 — EXECUTION</h2>'+article(s,'3.3','FIELD QUALITY CONTROL',reqs,exec_base['3.3'])+article(s,'3.4','PERFORMANCE VERIFICATION',reqs,exec_base['3.4'])))
 pages.append(page(s,'<h2 class="part">PART 3 — EXECUTION</h2>'+article(s,'3.5','COMMISSIONING',reqs,exec_base['3.5'])+article(s,'3.6','TRAINING AND CLOSEOUT',reqs,exec_base['3.6'])+'<div class="end">END OF SECTION</div>'))
 hp=R/'specs'/f'{s.replace(" ","")}_{slug(t)}.html'
 hp.write_text(f'<!doctype html><html><head><meta charset="utf-8"><title>{s} {e(t)}</title><style>{CSS}</style></head><body>{"".join(pages)}</body></html>')
 out=hp.with_suffix('.pdf')
 subprocess.run(['chromium','--headless','--no-sandbox','--disable-gpu','--run-all-compositor-stages-before-draw','--no-pdf-header-footer','--print-to-pdf='+str(out),hp.as_uri()],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
# refresh manifest
items=[]
for p in sorted(R.rglob('*')):
 if p.is_file() and p.name not in ['manifest.sha256','build.log']:
  items.append(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(R)}')
(R/'manifest.sha256').write_text('\n'.join(items)+'\n')
print('Corrected CSI hierarchy for 12 specifications')
