from pathlib import Path
import yaml
p=Path(__file__).resolve().parent/'project_bible.yaml'
b=yaml.safe_load(p.read_text())
rows=[('sections',len(b['sections']),12),('packages',len(b['packages']),22),('quality cases',len(b['quality_cases']),48),('conforming examples',len(b['conforming_examples']),40),('purchase orders',len(b['purchase_orders']),15),('activities',len(b['activities']),120),('commissioning tests',len(b['commissioning']),82),('schedule risks',len(b['risks']),4)]
print('PHASE 0 ASSERTION TABLE')
for n,a,e in rows: print(f'{n:24} {a:4} expected {e:4}  '+('PASS' if a==e else 'FAIL'))
assert all(a==e for _,a,e in rows)
