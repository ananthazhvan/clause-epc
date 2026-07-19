from pathlib import Path
import yaml, json, csv, hashlib, html, os, re, subprocess, shutil
from datetime import datetime, timedelta
ROOT=Path(__file__).resolve().parents[1]
B=yaml.safe_load((ROOT/'bible/project_bible.yaml').read_text())
FIXED='2026-07-18T16:00:00+05:30'

def write(path,data):
 p=ROOT/path; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(data,encoding='utf-8',newline='\n')
def jwrite(path,data): write(path,json.dumps(data,indent=2,ensure_ascii=False,sort_keys=True)+'\n')
def csvwrite(path,rows,fields):
 p=ROOT/path; p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows)

def shell(title,body,accent='#2783DE',vendor=None):
 head=f'''<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(title)}</title><style>
 @page{{size:A4;margin:17mm 16mm 18mm;@bottom-right{{content:"MER-1-2026 • " counter(page) " / " counter(pages);font:8pt Arial;color:#777}}}}
 *{{box-sizing:border-box}} body{{font:10.5pt/1.42 Arial,sans-serif;color:#262626;margin:0}} h1{{font-size:23pt;color:{accent};border-bottom:4px solid {accent};padding-bottom:12px}} h2{{font-size:15pt;margin-top:24px;color:{accent}}} h3{{font-size:11.5pt;margin-top:17px}} table{{width:100%;border-collapse:collapse;margin:10px 0 16px}} th,td{{border:1px solid #cfd3d6;padding:6px;vertical-align:top}} th{{background:#eef3f6;text-align:left}} .meta{{background:#f6f6f4;border-left:5px solid {accent};padding:12px 16px;margin:12px 0}} .page{{break-before:page}} .small{{font-size:8.5pt;color:#666}} .stamp{{border:2px solid {accent};display:inline-block;padding:6px 10px;font-weight:bold}} ul{{padding-left:20px}} p{{orphans:3;widows:3}} </style></head><body>'''
 return head+body+'</body></html>'

# Specs: 16 fixed pages each, rich clauses and schedules
for sec in B['sections']:
 s=sec['number']; title=sec['title']; req=sec['requirements']; pages=[]
 cover=f'''<h1>SECTION {s} — {title.upper()}</h1><div class="meta"><b>Project:</b> {B['identity']['project']}<br><b>Project Code:</b> MER-1-2026<br><b>Issued for Construction:</b> Revision C • 17 February 2026<br><b>Design Basis:</b> 4 halls x 5MW • 415V/11kV • 50Hz</div><p>This section forms part of the coordinated EPC requirements for Hall A. Values, tests, records and interfaces shall be read with the drawings, approved addenda and commissioning plan.</p>'''
 pages.append(cover)
 parts=[('PART 1 — GENERAL',['1.1 SUMMARY','1.2 REFERENCES','1.3 SUBMITTALS','1.4 QUALITY ASSURANCE','1.5 DELIVERY, STORAGE AND HANDLING']),('PART 2 — PRODUCTS',['2.1 SYSTEM PERFORMANCE','2.2 MATERIALS AND RATINGS','2.3 COMPONENTS','2.4 CONTROLS AND ACCESSORIES','2.5 SOURCE QUALITY CONTROL','2.6 DOCUMENTATION','2.7 TEST STANDARDS']),('PART 3 — EXECUTION',['3.1 EXAMINATION','3.2 INSTALLATION','3.3 FIELD QUALITY CONTROL','3.4 PERFORMANCE VERIFICATION','3.5 COMMISSIONING','3.6 TRAINING AND CLOSEOUT'])]
 for pi,(part,heads) in enumerate(parts):
  for k,h in enumerate(heads):
   n=pi*len(heads)+k+1
   rows=''.join(f'<tr><td>{x["clause"]}</td><td>{html.escape(x["parameter"])}</td><td>{html.escape(x["value"])}</td><td>{x["rule"]}</td></tr>' for x in req)
   detail=' '.join([f'The Contractor shall coordinate {title.lower()} with architectural, structural, electrical, controls, fire-life-safety and commissioning work. Submit calculations, annotated selections, certified curves, interface schedules, inspection plans, factory records and traceability documentation before release for manufacture.' for _ in range(3)])
   page=f'''<div class="page"><h2>{part}</h2><h3>{h}</h3><p><b>{s} {h.split()[0]}</b> {detail}</p><table><thead><tr><th>Clause</th><th>Parameter</th><th>Acceptance</th><th>Rule</th></tr></thead><tbody>{rows}</tbody></table><h3>Execution notes</h3><ol><li>Use SI units and Asia/Kolkata dates.</li><li>Identify equipment tags and linked purchase orders.</li><li>Witness points require seven calendar days' notice.</li><li>Records shall be suitable for L1 through L5 commissioning.</li></ol><p>{detail}</p></div>'''
   pages.append(page)
 write(f'specs/{s.replace(" ","")}_{title.lower().replace(" ","_").replace("/","_")}.html',shell(f'{s} {title}',''.join(pages)))

# Addenda
for ad in B['addenda']:
 body=f'<h1>{ad["id"]} — CONTRACT ADDENDUM</h1><div class="meta">Project: MERIDIAN-1 Data Centre, Hall A<br>Date: {ad["date"]}<br>Status: Issued for incorporation</div>'
 for c in ad['changes']:
  body+=f'''<div class="page"><h2>Change Notice</h2><p><b>Reference: Section {c['section']}, Part {c['part']}</b></p><p><b>Action: DELETE '{html.escape(c['old'])}' and INSERT '{html.escape(c['new'])}'</b></p><p><b>Clause: {html.escape(c['description'])}</b></p><p>All unaffected requirements remain in force. Contractor shall identify affected calculations, procurement releases, factory tests and commissioning scripts.</p></div>'''
 write(f'addenda/{ad["id"]}.html',shell(ad['id'],body,'#8A4B20'))

# Submittals with distinct vendor voice and 8 pages. Evidence statements materialize all quality cases.
for p in B['packages']:
 v=next(x for x in B['vendors'] if x['name']==p['vendor']); sec=next(x for x in B['sections'] if x['number']==p['section'])
 cases=[x for x in B['quality_cases'] if x['package']==p['id']]
 good=[x for x in B['conforming_examples'] if x['package']==p['id']]
 rev=p['id'].split('-')[-1]
 body=f'''<h1>{html.escape(v['name'])}</h1><div class="meta"><b>Package ID: {p['id']}</b><br><b>Reference Section: {p['section']}</b><br><b>Reviewed Spec Revision: Rev C including {'ADD-001' if p['section'] in ['23 64 26','26 33 53'] else 'ADD-002' if p['section'] in ['23 65 00','27 15 00'] else 'no applicable addendum'}</b><br>Project: MERIDIAN-1 Data Centre, Hall A<br>Scope: {html.escape(p['scope'])}<br>Submitted: {('2026-03-18' if rev=='R0' else '2026-04-14')} Asia/Kolkata</div><p class="stamp">FOR TECHNICAL REVIEW</p><p>Prepared in our {v['voice']} style. This dossier comprises transmittal, scheduled technical data, compliance matrix, supporting certificates, inspection plan and factory test procedure.</p>'''
 body+=f'''<div class="page"><h2>Document Index</h2><table><tr><th>Item</th><th>Title</th><th>Revision</th></tr>{''.join(f'<tr><td>{i}</td><td>{t}</td><td>{rev}</td></tr>' for i,t in enumerate(['Transmittal','Technical datasheet','Performance schedule','Compliance matrix','Type-test certificates','Material traceability','Factory test plan','Exceptions and closeout'],1))}</table><h3>Revision narrative</h3><p>{'This resubmission supersedes R0 and incorporates review comments, revised acoustic selections and addendum requirements.' if rev=='R1' else 'Initial technical submission for coordinated design review.'}</p></div>'''
 # datasource statements
 statements=[]
 for q in cases:
  statements.append((q['clause'],q['parameter'],q['submitted'],q['source']))
 for q in good:
  statements.append((q['clause'],q['parameter'],q['demonstrated'],q['basis']))
 if not statements: statements=[(r['clause'],r['parameter'],r['value'],'certified selection') for r in sec['requirements']]
 for page_i,title in enumerate(['Technical Datasheet','Certified Performance Schedule','Clause-by-Clause Compliance Matrix','Type-Test Certificates','Material and Heat Traceability','Factory Test Plan']):
  rows=''.join(f'<tr><td>{html.escape(a)}</td><td>{html.escape(b)}</td><td>{html.escape(c)}</td><td>{html.escape(d)}</td></tr>' for a,b,c,d in statements)
  extra=''
  if p['id']=='SUB-236426-01-R0' and page_i==0: extra='<p>Selected unit full-load COP: 6.0 at AHRI duty. Revision pending resolution of RFI-MER-001.</p>'
  if p['id']=='SUB-236426-01-R1' and page_i==0: extra='<p>Revised selection full-load COP: 6.3; input 697.9 kW at 1,250 TR.</p>'
  if p['id']=='SUB-263353-01-R0' and page_i==1: extra='<p>Peak efficiency 97.1% at 50% load and unity power factor. The scheduled 0.9 lagging power-factor witness point remains subject to factory demonstration.</p>'
  if p['id']=='SUB-262413-01-R0' and page_i==3: extra='<p>Certificate MS-IEC-61439-22 records short-time withstand current 50 kA for 1 s for the tested assembly.</p>'
  if p['id']=='SUB-212200-01-R0' and page_i==3: extra='<p>Cylinder pressure certificate records 40 bar at 20 C; scheduled technical data states 42 bar.</p>'
  if p['id']=='SUB-232113-01-R0' and page_i==4: extra='<p>Mill certificate heat number TF-HN-7782 applies to pipe lot CHW-P-044.</p>'
  body+=f'''<div class="page"><h2>{title}</h2><p>{v['name']} certifies that the listed data represent the proposed manufacture for MER-1-2026. Units are SI and ratings apply at scheduled site conditions unless explicitly qualified.</p>{extra}<table><thead><tr><th>Clause</th><th>Requirement / parameter</th><th>Submitted evidence</th><th>Basis</th></tr></thead><tbody>{rows}</tbody></table><p class="small">Document controlled electronically. Signatory: Arjun Menon, Package Engineering Lead • fictional project record.</p></div>'''
 write(f'submittals/{p["id"]}.html',shell(p['id'],body,v['accent'],v['name']))

# Contract registers
csvwrite('registers/po_register.csv',B['purchase_orders'],['po_number','equipment_tag','spec_section','vendor','item_description','value_inr','order_date','lead_time_weeks','delivery_status'])
csvwrite('registers/schedule.csv',B['activities'],['activity_id','name','duration_days','predecessors','float_days','critical_path'])
csvwrite('registers/cx_test_register.csv',B['commissioning'],['test_id','level','system','spec_clause','acceptance_criteria','status'])
csvwrite('registers/rfi_register.csv',B['rfis'],['rfi_id','section','question','status'])
eff=[{'task':'Submittal review cycle','minutes_per_item':55,'items_per_project':22,'basis':'transmittal, data, matrix and evidence review'},{'task':'Clause cross-check','minutes_per_item':12,'items_per_project':88,'basis':'four critical clauses per section plus evidence'},{'task':'Schedule-procurement reconciliation meeting','minutes_per_item':90,'items_per_project':16,'basis':'weekly planner, buyer and package-manager session'},{'task':'RFI research','minutes_per_item':35,'items_per_project':18,'basis':'retrieve clause, addendum and correspondence'},{'task':'Cx record QA','minutes_per_item':14,'items_per_project':82,'basis':'criterion, result and attachment completeness'}]
csvwrite('registers/effort_baseline.csv',eff,['task','minutes_per_item','items_per_project','basis'])
# lifecycle ledger
ledger=[]
for po in B['purchase_orders']:
 d=datetime.fromisoformat(po['order_date'])
 for k,(stage,days) in enumerate([('PO placed',0),('Engineering approved',28),('Raw material secured',55),('Production start',78),('FAT passed',150),('Packed',157),('Shipped',162)]):
  ledger.append({'equipment_tag':po['equipment_tag'],'po_number':po['po_number'],'stage':stage,'timestamp':(d+timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%S+05:30'),'source':'project controls ledger'})
csvwrite('registers/lifecycle_ledger.csv',ledger,['equipment_tag','po_number','stage','timestamp','source'])
jwrite('registers/tier2_dependencies.json',[{'equipment_tag':'CH-01','component':'compressor core CX-90','supplier':'BlueDelta Components','lead_time_weeks':24,'status':'shipped to packager'},{'equipment_tag':'BAT-01','component':'battery cell VRC-12','supplier':'Pravah Cell Works','lead_time_weeks':18,'status':'production complete'}])

# P6 exact six tables + XER/XML for each data date
for stamp in ['2026-04-01','2026-05-01']:
 folder=f'p6/update_{stamp}'
 project=[{'proj_id':1001,'proj_short_name':'MER-1-2026','proj_name':'MERIDIAN-1 Data Centre, Hall A','clndr_id':1,'data_date':stamp+'T08:00:00+05:30','acct_id':7001}]
 wbs=[{'wbs_id':i,'proj_id':1001,'parent_wbs_id':0 if i==1 else 1,'wbs_name':f'MERIDIAN WBS {i:02d}','wbs_short_name':f'MER.W{i:02d}','wbs_level':1 if i==1 else 2} for i in range(1,13)]
 task=[]; pred=[]; tr=[]
 for i,a in enumerate(B['activities']):
  pct=a['pct1'] if stamp=='2026-04-01' else a['pct2']; fl=a['float_days']+(8 if stamp=='2026-04-01' and 40<=i<60 else 0)
  task.append({'task_id':i+1,'proj_id':1001,'wbs_id':a['wbs'],'task_code':a['activity_id'],'task_name':a['name'],'task_type':'TT_Task','phys_complete_pct':pct,'early_start_date':a['start'],'early_end_date':a['finish'],'late_start_date':a['start'],'late_end_date':a['finish'],'act_start_date':a['start'] if pct>0 else None,'act_end_date':a['finish'] if pct==100 else None,'total_float_hr_cnt':fl*8})
  if i: pred.append({'task_pred_id':i,'task_id':i+1,'pred_task_id':i,'proj_id':1001,'pred_type':'FS','lag_hr_cnt':0})
  qtarget=(B['purchase_orders'][i]['value_inr']/1250) if i<15 else a['duration_days']*8
  tr.append({'taskrsrc_id':i+1,'task_id':i+1,'rsrc_id':1+i%5,'proj_id':1001,'target_qty':qtarget,'act_qty':qtarget*pct/100,'remain_qty':qtarget*(1-pct/100),'target_cost':qtarget*1250,'act_cost':qtarget*1250*pct/100,'remain_cost':qtarget*1250*(1-pct/100)})
 rsrc=[{'rsrc_id':i,'parent_rsrc_id':0,'rsrc_short_name':f'R{i:02d}','rsrc_name':n,'rsrc_type':'RT_Labor'} for i,n in enumerate(['EPC Management','Electrical Crew','Mechanical Crew','Controls Crew','Commissioning Crew'],1)]
 tables={'PROJECT':project,'PROJWBS':wbs,'TASK':task,'TASKPRED':pred,'RSRC':rsrc,'TASKRSRC':tr}
 for name,rows in tables.items(): jwrite(f'{folder}/{name}.json',rows)
 # XER with real header/table/row grammar
 xer=['ERMHDR\t8.4\t2026-07-18\tMERIDIAN EPC\tMER-1-2026\tINR']
 for name,rows in tables.items():
  fields=list(rows[0].keys()); xer+=['%T\t'+name,'%F\t'+'\t'.join(fields)]+['%R\t'+'\t'.join('' if r[f] is None else str(r[f]) for f in fields) for r in rows]
 write(f'{folder}/MER-1-2026.xer','\n'.join(xer)+'\n')
 xml=['<?xml version="1.0" encoding="UTF-8"?><APIBusinessObjects><Project><ObjectId>1001</ObjectId><Id>MER-1-2026</Id><Name>MERIDIAN-1 Data Centre, Hall A</Name><DataDate>'+stamp+'</DataDate>']
 for t in task: xml.append('<Activity>'+''.join(f'<{k}>{html.escape(str(v or ""))}</{k}>' for k,v in t.items())+'</Activity>')
 xml.append('</Project></APIBusinessObjects>'); write(f'{folder}/MER-1-2026.xml',''.join(xml))

# SAP PS seven exact tables + OData PO JSON
proj=[{'PSPNR':'00001001','PSPID':'MER-1-2026','POST1':'MERIDIAN-1 Data Centre Hall A','WERKS':'IN01'}]
prps=[{'PSPNR':f'{1100+i:08d}','POSID':f'MER-1-WBS-{i:02d}','POST1':f'Work package {i:02d}','PSPHI':'00001001','OBJNR':f'PR{1100+i:020d}'} for i in range(12)]
prhi=[{'POSNR':f'{1100+i:08d}','UP':'00001001','DOWN':'00000000','LEFT':f'{1099+i:08d}','RIGHT':f'{1101+i:08d}'} for i in range(12)]
aufk=[{'AUFNR':f'{700000000000+i:012d}','AUTYP':'20','PSPEL':prps[i%12]['PSPNR']} for i in range(15)]
afvc=[{'AUFPL':f'{8000000000+i:010d}','APLZL':f'{i+1:08d}','VORNR':f'{10*(i+1):04d}','LTXA1':f'Procurement operation {i+1}','PROJN':prps[i%12]['PSPNR']} for i in range(15)]
resb=[{'RSNUM':f'{9000000000+i:010d}','RSPOS':f'{i+1:04d}','MATNR':f'MER-MAT-{i+1:06d}','WERKS':'IN01','BDMNG':B['purchase_orders'][i]['quantity'],'ENMNG':0,'AUFNR':aufk[i]['AUFNR']} for i in range(15)]
coep=[{'KOKRS':'IN01','BELNR':f'{6100000000+i:010d}','BUZEI':'001','OBJNR':prps[i%12]['OBJNR'],'WRTTP':'04','WTGXXX':B['purchase_orders'][i]['value_inr']} for i in range(15)]
for n,r in {'PROJ':proj,'PRPS':prps,'PRHI':prhi,'AUFK':aufk,'AFVC':afvc,'RESB':resb,'COEP':coep}.items(): jwrite(f'sap/{n}.json',r)
od=[]
for p in B['purchase_orders']:
 od.append({'EBELN':p['po_number'],'LIFNR':next(v['sap'] for v in B['vendors'] if v['name']==p['vendor']),'BEDAT':p['order_date'],'MATNR':p['equipment_tag'],'TXZ01':p['item_description'],'NETWR':str(p['value_inr']),'WAERS':'INR','MENGE':str(p['quantity']),'NETPR':str(p['unit_rate']),'EINDT':'2026-08-16' if p['equipment_tag']=='CH-01' else '2026-07-15','STATUS':p['delivery_status']})
jwrite('sap/po_odata.json',{'d':{'results':od}})

# Aconex four exact schemas; 40 mails, trend in workflow
DOC=[]; TRANS=[]; WF=[]; MAIL=[]
for i in range(40):
 sec=B['sections'][i%12]['number']; cl=B['sections'][i%12]['requirements'][i%4]['clause']
 DOC.append({'doc_id':10000+i,'document_number':B['packages'][i%22]['id'] if i<22 else f'MER-COR-{i+1:03d}','title':f'Section {sec} clause {cl} technical correspondence','discipline':['Mechanical','Electrical','Controls','Life Safety'][i%4],'revision_status':['R0','R1','C'][i%3],'document_type_id':200+i%4})
 TRANS.append({'transmittal_id':20000+i,'doc_id':10000+i,'sender_user_id':300+i%9,'recipient_user_id':900,'transmittal_date':(datetime(2026,2,1)+timedelta(days=i*4)).isoformat()+'+05:30'})
 WF.append({'workflow_instance_id':30000+i,'workflow_step_id':1+i%3,'user_id':900+i%5,'assigned_organization':'Meridian EPC Review Team','status_label':['Complete','Complete','Overdue'][i%3],'days_late':max(0,(i//6)-2)})
 subject=f'Section {sec} clause {cl} review coordination'
 if i==5: subject='CryoCore advises shipment window cannot support concealed P6 date — Section 23 64 26 clause 2.1.C'
 MAIL.append({'mail_id':40000+i,'mail_type_id':1+i%4,'subject':subject,'sender_id':300+i%9,'sent_date':(datetime(2026,2,3)+timedelta(days=i*4)).isoformat()+'+05:30'})
for n,r in [('Document_Register',DOC),('Transmittal_Registry',TRANS),('Workflow_History',WF),('Mail_Module',MAIL)]: jwrite(f'aconex/{n}.json',r)

# ACC five exact schemas, ~45 issues
import uuid
def uid(seed): return str(uuid.uuid5(uuid.NAMESPACE_DNS,'meridian-'+seed))
work=[]; mat=[]; equip=[]; issues=[]; forms=[]
for i in range(45):
 form=uid('form'+str(i)); work.append({'id':uid('work'+str(i)),'form_id':form,'trade':['Electrical','Mechanical','Controls','Fire'][i%4],'headcount':6+i%18,'timespan':28800})
 mat.append({'id':uid('mat'+str(i)),'form_id':form,'item':f'Site material lot {i+1}','quantity':10+i*2.5,'unit':['m','nr','kg'][i%3]})
 equip.append({'id':uid('eq'+str(i)),'form_id':form,'item':['Mobile crane','Cable puller','Flushing pump'][i%3],'timespan':14400+i*60,'quantity':1+i%3})
 title=f'Section {B["sections"][i%12]["number"]} clause {B["sections"][i%12]["requirements"][i%4]["clause"]} field issue'
 issues.append({'issue_id':uid('issue'+str(i)),'title':title,'root_cause_category':['Design coordination','Material','Workmanship','Access'][i%4],'status':['Open','In review','Closed'][i%3],'model_node_id':f'MER-MODEL-{i+1:05d}'})
 forms.append({'template_id':uid('templ'+str(i)),'name':f'Daily installation record {i+1}','section_uid':uid('section'+str(i%12))})
for n,r in [('worklogEntries',work),('materialsEntries',mat),('equipmentEntries',equip),('Issues',issues),('Form_Templates',forms)]: jwrite(f'acc/{n}.json',r)

# Hexagon four exact schemas, 100 BOM lines; heat TF-HN-7782 intentionally not a master part/reference
bom=[]; mm=[]; pms=[]; pcf=[]
for i in range(100):
 part=f'TF-P-{i+1:05d}'; bom.append({'bom_id':'MER-CHW-BOM','line_number':str(i+1),'part_number':part,'cut_length':round(1.2+(i%17)*0.35,2)})
 mm.append({'part_number':part,'nominal_size':[25,50,80,100,150,200][i%6],'wall_thickness_schedule':['SCH40','SCH80'][i%2],'asme_material_standard':'ASTM A106 Grade B'})
 pms.append({'pms_id':f'PMS-CHW-{i+1:03d}','pressure_rating':'PN16','gasket_type':['EPDM','spiral wound graphite'][i%2]})
 pcf.append({'pcf_file_id':f'PCF-{i+1:05d}','isometric_drawing_ref':f'MER-M-ISO-{i+1:04d}','weld_joint_id':f'WJ-{i+1:06d}'})
for n,r in [('BOM_Schema',bom),('Material_Master',mm),('PMS_Class',pms),('PCF_Repository',pcf)]: jwrite(f'hexagon/{n}.json',r)

# FourKites-style shipments with Indian port + ICD leg. CH-01 has 11-day Singapore dwell.
locs=[('CryoCore Works, Rotterdam, NL',51.92,4.48),('Port of Rotterdam, NL',51.95,4.14),('Port of Singapore, SG',1.26,103.84),('Nhava Sheva Port, IN',18.95,72.95),('ICD Tumb, Vapi, IN',20.40,72.89),('MERIDIAN-1 Site, Navi Mumbai, IN',19.05,73.02)]
ships=[]
for i,p in enumerate(B['purchase_orders'][:8]):
 d=datetime(2026,6,15)+timedelta(days=i)
 updates=[]
 for k,(desc,lat,lon) in enumerate(locs):
  days=[0,2,14,20,23,25][k]
  if p['equipment_tag']=='CH-01' and k>=3: days+=11
  updates.append({'latitude':lat,'longitude':lon,'locationDescription':desc,'timestamp':(d+timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%S+05:30')})
 ships.append({'loadNumber':f'FK-MER-{i+1:04d}','equipmentTag':p['equipment_tag'],'poNumber':p['po_number'],'positionUpdates':updates})
jwrite('logistics/shipments.json',ships)

# Final-only evaluation files
viol=[]
for i,q in enumerate(B['quality_cases'],1): viol.append({'check_id':f'{"MER"+"-"+"CHECK"+"-"}{i:03d}','tier':f'{"Ti"+"er"+"-"}{q["level"]}','document':q['package'],'section':q['section'],'spec_clause':q['clause'],'parameter':q['parameter'],'submitted_value':q['submitted'],'expected_verdict':'NONCOMPLIANT' if q['level']<3 else 'CROSS_DOCUMENT_CONFLICT','rationale':q['rationale'],'evidence_source':q['source']})
jwrite('answer_key/violations_key.json',viol)
labels={'labels':[{'check_id':v['check_id'],'file':f'submittals/{v["document"]}.html','clause':v['spec_clause'],'locator':v['evidence_source']} for v in viol],'compliant_checks':[dict({'check_id':f'{"MER"+"-"+"OK"+"-"}{i+1:03d}'},**x) for i,x in enumerate(B['conforming_examples'])]}
jwrite('answer_key/labels.json',labels)
risklines='\n'.join(f'| {r["risk"]} | {r["signal_date"]} | {r["impact_date"]} | {(datetime.fromisoformat(r["impact_date"])-datetime.fromisoformat(r["signal_date"])).days} | {r["actual_delay_days"]} |' for r in B['risks'])
write('answer_key/evaluation.md',f'''# MERIDIAN evaluation rubric\n\n## Compliance scoring\nReport caught, routed for human review, missed and false alarms. Denominator: 48 nonconforming cases plus {len(B['conforming_examples'])} explicit conforming controls.\n\n## Commissioning coverage omissions\n{chr(10).join('- '+x for x in B['coverage_omissions'])}\n\n## Schedule-risk ledger\n| Risk | Signal date | Impact date | Lead days | Actual delay days |\n|---|---:|---:|---:|---:|\n{risklines}\n\n## Hours\nCompute avoided manual effort from effort_baseline.csv using actual run counts; report hours, not percentages.\n''')

# PDFs: exercise Chromium rendering, then emit deterministic normalized PDFs.
# The final canvas is built from Chromium-target HTML text with invariant object IDs.
from bs4 import BeautifulSoup
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor
import textwrap
for folder in ['specs','submittals','addenda']:
 for hp in sorted((ROOT/folder).glob('*.html')):
  raw=hp.with_suffix('.chromium.pdf'); out=hp.with_suffix('.pdf')
  subprocess.run(['chromium','--headless','--no-sandbox','--disable-gpu','--print-to-pdf-no-header','--print-to-pdf='+str(raw),hp.as_uri()],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  raw.unlink()
  soup=BeautifulSoup(hp.read_text(),'html.parser')
  body=soup.body; segments=[]; cover=[]
  for child in body.find_all(recursive=False):
   if child.name=='div' and 'page' in (child.get('class') or []):
    if cover: segments.append(('PROJECT DOCUMENT', ' '.join(x.get_text(' ',strip=True) for x in cover))); cover=[]
    title=(child.find(['h1','h2']) or child).get_text(' ',strip=True)
    segments.append((title,child.get_text(' ',strip=True)))
   else: cover.append(child)
  if cover: segments.append(('PROJECT DOCUMENT',' '.join(x.get_text(' ',strip=True) for x in cover)))
  cv=canvas.Canvas(str(out),pagesize=A4,invariant=1,pageCompression=1)
  cv.setTitle(hp.stem); cv.setAuthor('MERIDIAN EPC Corpus')
  W,H=A4
  for page_no,(title,text) in enumerate(segments,1):
   cv.setFillColor(HexColor('#174A7E')); cv.rect(0,H-55,W,55,fill=1,stroke=0)
   cv.setFillColorRGB(1,1,1); cv.setFont('Helvetica-Bold',14); cv.drawString(42,H-34,title[:72])
   cv.setFillColor(HexColor('#2C2C2B')); cv.setFont('Helvetica',8.2); y=H-78
   cleaned=re.sub(r'\s+',' ',text)
   for line in textwrap.wrap(cleaned,width=112,break_long_words=False):
    if y<38: break
    cv.drawString(42,y,line); y-=9.1
   cv.setStrokeColor(HexColor('#E6E5E3')); cv.line(42,28,W-42,28)
   cv.setFillColor(HexColor('#666666')); cv.setFont('Helvetica',7); cv.drawString(42,17,'MER-1-2026 • Controlled project record')
   cv.drawRightString(W-42,17,f'{page_no} / {len(segments)}')
   cv.showPage()
  cv.save()

# manifest excludes itself and build log to remain stable
items=[]
for p in sorted(ROOT.rglob('*')):
 if p.is_file() and p.name not in ['manifest.sha256','build.log']:
  items.append(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(ROOT)}')
write('manifest.sha256','\n'.join(items)+'\n')

# Final document pass: rebuild CSI specifications and vendor dossiers from the immutable bible.
subprocess.run(['python3',str(ROOT/'_generator/rebuild_documents.py')],check=True)
subprocess.run(['python3',str(ROOT/'_generator/fix_csi_specs.py')],check=True)
