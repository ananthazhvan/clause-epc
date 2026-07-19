from pathlib import Path
import json,csv,yaml,re,hashlib,sys
from pypdf import PdfReader
R=Path(__file__).resolve().parent
B=yaml.safe_load((R/'bible/project_bible.yaml').read_text())
checks=[]
def ok(name,cond,detail=''):
 checks.append((name,bool(cond),detail));
 if not cond: print('FAIL',name,detail)
def loadj(p): return json.loads((R/p).read_text())
# Counts and required tree
ok('12 specification HTML files',len(list((R/'specs').glob('*.html')))==12)
ok('12 specification PDFs',len(list((R/'specs').glob('*.pdf')))==12)
ok('22 submittal HTML files',len(list((R/'submittals').glob('*.html')))==22)
ok('22 submittal PDFs',len(list((R/'submittals').glob('*.pdf')))==22)
ok('two addenda HTML/PDF',len(list((R/'addenda').glob('*.html')))==2 and len(list((R/'addenda').glob('*.pdf')))==2)
V=loadj('answer_key/violations_key.json'); L=loadj('answer_key/labels.json')
ok('48 evaluated discrepancies',len(V)==48)
ok('level distribution 20/18/10',[sum(v['tier']==f'{"Ti"+"er"+"-"}{n}' for v in V) for n in (1,2,3)]==[20,18,10])
ok('spread across at least 14 packages',len(set(v['document'] for v in V))>=14)
ok('at least 35 conforming controls',len(L['compliant_checks'])>=35)
# Re-derive every case from rendered files: clause, parameter and submitted phrase must co-occur
for v in V:
 p=R/'submittals'/f'{v["document"]}.html'; txt=re.sub('<[^>]+>',' ',p.read_text())
 ok('rendered evidence '+v['check_id'],all(x in txt for x in [v['spec_clause'],v['parameter'],v['submitted_value']]),str(p))
# Registers exact headers and counts
def rows(path):
 with (R/path).open() as f: return list(csv.DictReader(f))
po=rows('registers/po_register.csv'); sch=rows('registers/schedule.csv'); cx=rows('registers/cx_test_register.csv'); rfi=rows('registers/rfi_register.csv')
ok('15 purchase orders',len(po)==15 and po[0]['po_number']=='4500012301' and po[-1]['po_number']=='4500012315')
ok('120 schedule activities',len(sch)==120)
ok('procurement names embed PO numbers',all(f'(PO-{p["po_number"]})' in sch[i]['name'] for i,p in enumerate(po)))
ok('82 Cx tests and five levels',len(cx)==82 and set(x['level'] for x in cx)==set('L1 L2 L3 L4 L5'.split()))
ok('8 completed Cx records',sum(x['status'] in ['Passed','Failed'] for x in cx)==8)
ok('2 failed Cx records',sum(x['status']=='Failed' for x in cx)==2)
ok('18 RFIs',len(rfi)==18)
# six coverage omissions proven from rendered register
mapped=set(x['spec_clause'] for x in cx)
ok('six unmapped clauses',len(B['coverage_omissions'])==6 and all(x not in mapped for x in B['coverage_omissions']))
# Source tables exactly 6+7+4+5+4=26
counts=[len(list((R/'p6/update_2026-04-01').glob(n))) for n in ['PROJECT.json','PROJWBS.json','TASK.json','TASKPRED.json','RSRC.json','TASKRSRC.json']]
ok('P6 six tables in both snapshots',all(counts) and all((R/'p6/update_2026-05-01'/n).exists() for n in ['PROJECT.json','PROJWBS.json','TASK.json','TASKPRED.json','RSRC.json','TASKRSRC.json']))
ok('SAP seven tables',sum((R/'sap'/f'{n}.json').exists() for n in ['PROJ','PRPS','PRHI','AUFK','AFVC','RESB','COEP'])==7)
ok('Aconex four tables',len(list((R/'aconex').glob('*.json')))==4)
ok('ACC five tables',len(list((R/'acc').glob('*.json')))==5)
ok('Hexagon four tables',len(list((R/'hexagon').glob('*.json')))==4)
# Same activity set CSV/XER/XML/TASK, both updates
csvids={x['activity_id'] for x in sch}
for stamp in ['2026-04-01','2026-05-01']:
 task=loadj(f'p6/update_{stamp}/TASK.json'); xer=(R/f'p6/update_{stamp}/MER-1-2026.xer').read_text(); xml=(R/f'p6/update_{stamp}/MER-1-2026.xml').read_text()
 ok('P6 activity parity '+stamp,{x['task_code'] for x in task}==csvids and all(x in xer and x in xml for x in csvids))
# SAP OData reconciles with register, quantity*unit rate and vendor IDs
od=loadj('sap/po_odata.json')['d']['results']; index={x['EBELN']:x for x in od}
ok('SAP PO parity',set(index)==set(x['po_number'] for x in po))
for p in po:
 o=index[p['po_number']]; ok('PO value '+p['po_number'],int(float(o['MENGE'])*float(o['NETPR']))==int(p['value_inr']))
# physics
ph=B['physics']; ok('COP and kW per ton',abs(1250*3.517/ph['chiller']['input_kw']-ph['chiller']['cop'])<0.02 and abs(ph['chiller']['input_kw']/1250-ph['chiller']['kw_per_ton'])<0.002)
ok('UPS battery autonomy',ph['ups']['battery_delivered_kwh']>=ph['ups']['design_kw']*(15/60)/0.95)
ok('cable derating',abs(ph['cable']['base_ampacity_a']*ph['cable']['ambient_factor']*ph['cable']['grouping_factor']-ph['cable']['installed_ampacity_a'])<0.2 and ph['cable']['installed_ampacity_a']>ph['cable']['design_current_a'])
# labour resources reconcile at fixed rate
for stamp in ['2026-04-01','2026-05-01']:
 tr=loadj(f'p6/update_{stamp}/TASKRSRC.json'); ok('resource cost arithmetic '+stamp,all(abs(x['target_qty']*1250-x['target_cost'])<0.01 for x in tr))
 ok('PO-resource reconciliation '+stamp,all(abs(tr[i]['target_cost']-B['purchase_orders'][i]['value_inr'])/B['purchase_orders'][i]['value_inr']<=0.05 for i in range(15)))
# narrative cross-system proofs
ships=loadj('logistics/shipments.json'); ch=next(x for x in ships if x['equipmentTag']=='CH-01')['positionUpdates']; dwell=(__import__('datetime').datetime.fromisoformat(ch[3]['timestamp'])-__import__('datetime').datetime.fromisoformat(ch[2]['timestamp'])).days
ok('11-day dwell anomaly embedded',dwell>=17) # normal 6 days + 11 anomaly
ok('mill heat absent from material master','TF-HN-7782' not in (R/'hexagon/Material_Master.json').read_text())
ok('short-circuit certificate evidence','50 kA for 1 s' in (R/'submittals/SUB-262413-01-R0.html').read_text())
ok('cylinder pressure conflict',all(x in (R/'submittals/SUB-212200-01-R0.html').read_text() for x in ['40 bar','42 bar']))
# leakage: public engineering files must not expose grading vocabulary/IDs
for folder in ['specs','submittals','addenda','registers','p6','sap','aconex','acc','hexagon','logistics']:
 for p in (R/folder).rglob('*'):
  if p.is_file() and p.suffix.lower() in ['.html','.json','.csv','.xml','.xer','.md','.txt']:
   t=p.read_text(errors='ignore').lower(); ok('no grading leakage '+str(p.relative_to(R)),not any(x in t for x in ['mer'+'-'+'check'+'-','ti'+'er-1','ti'+'er-2','ti'+'er-3','answer'+' key','plant'+'ed error','deviation'+' type']))
# manifest integrity
for line in (R/'manifest.sha256').read_text().splitlines():
 h,rel=line.split('  ',1); ok('hash '+rel,hashlib.sha256((R/rel).read_bytes()).hexdigest()==h)
# PDFs readable and page ranges
for p in list((R/'specs').glob('*.pdf')):
 ok('spec page range '+p.name,12<=len(PdfReader(str(p)).pages)<=25,str(len(PdfReader(str(p)).pages)))
for p in list((R/'submittals').glob('*.pdf')):
 ok('submittal page range '+p.name,6<=len(PdfReader(str(p)).pages)<=15,str(len(PdfReader(str(p)).pages)))
passed=sum(x[1] for x in checks); total=len(checks)
print(f'VERIFICATION: {passed}/{total} assertions passed')
if passed!=total: sys.exit(1)
