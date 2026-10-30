import json,csv,sqlite3,hashlib
from pathlib import Path
from datetime import date
R=Path(__file__).resolve().parent
rows=json.loads((R/'recalls.json').read_text(encoding='utf-8'))
assert len(rows)==211
assert len({r['id'] for r in rows})==211
assert len({r['source_url'] for r in rows})==211
assert all(r['source_url'].startswith(('https://www.samrdprc.org.cn/xfpzh/xfpzhgg/','https://www.samrdprc.org.cn/fzlm/zhgg/xfpzhgg/')) for r in rows)
for r in rows:
 date.fromisoformat(r['published_date'])
 assert r['quantity']>0
 assert r['review_status']=='已完成逐条文本复核'
 assert r['category']!='待分类' and r['risk_tags']
 assert r['batch_review_status'] and r['batch_review_note']
 assert r['review_evidence']['batch_raw']==r['batch_raw']
 assert not r['automated_match_enabled']
 for field in ['producer','product_name','model_raw','production_dates_raw','defect_raw','consequence_raw','remedy_raw']:
  if field=='model_raw' and r['id']=='t20251125_114605':
   assert r[field] is None and 'missing:model_raw' in r['quality_flags']
   continue
  assert r[field],(r['id'],field)
  assert 'L20:' not in r[field] and '上一篇' not in r[field],(r['id'],field)
 fragments=(R/r['extract_file']).read_text(encoding='utf-8').split('-'*80)
 assert any(hashlib.sha256(x.encode()).hexdigest()==r['extract_sha256'] for x in fragments),r['id']
with (R/'recalls.csv').open(encoding='utf-8-sig',newline='') as f:
 csvrows=list(csv.DictReader(f))
assert len(csvrows)==len(rows)
for a,b in zip(rows,csvrows):
 assert a['source_url']==b['source_url'] and str(a['quantity'])==b['quantity']
db=sqlite3.connect(R/'recalls.sqlite3')
assert db.execute('SELECT COUNT(*) FROM recalls').fetchone()[0]==len(rows)
assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
assert {x[0] for x in db.execute('SELECT source_url FROM recalls')}=={r['source_url'] for r in rows}
db.close()
byid={r['id']:r for r in rows}
assert byid['t20250514_113494']['quantity']==222+35+360
assert byid['t20250403_113209']['quantity']==50+48+40+50
assert byid['t20250224_113020']['quantity']==20
assert byid['t20250606_113609']['defect_raw'].startswith('电源连接')
assert byid['t20250514_113504']['quantity']==100
assert len(byid['t20250514_113504']['risk_tags'])>=2
print('PASS: 211 reviewed notices; provenance hashes; fields; CSV/JSON/SQLite consistency; complex quantities; multiline parsing.')

assert byid['t20250606_113607']['risk_tags']==['防护失效']
assert byid['t20250430_113423']['batch_raw']=='20240316'
assert byid['t20250818_114034']['quantity']==25
scopes=byid['t20250403_113209']['scope_details']['groups']
assert len(scopes)==4
assert scopes[1]['model']=='QF25-30W' and scopes[1]['batches']==['LED-A210605-04']
assert len(byid['t20250430_113433']['scope_details']['groups'][0]['dates'])==2
assert byid['t20250730_113929']['scope_details']['batch_range']['start']=='01'
assert byid['t20250514_113494']['scope_details']['production_end'] is None
assert len(json.loads((R/'quarantine.json').read_text(encoding='utf-8')))==5
print('PASS: all review decisions, source field corrections, model/batch associations, isolated dates and ambiguous ranges.')

assert byid["t20260401_115307"]["quantity"]==140
assert len(byid["t20260401_115307"]["scope_details"]["groups"])==3
assert byid["t20260109_114962"]["batch_raw"] is None
assert byid["t20260109_114962"]["consequence_raw"].startswith("增塑剂")
assert byid["t20260109_114964"]["quantity_unit"]=="盒"
assert byid["t20260211_115179"]["scope_assessment"]=="范围细节需补充确认"

assert byid['t20251120_114587']['quantity']==89400
assert byid['t20251201_114643']['quantity']==76
assert byid['t20260604_115619']['quantity']==20
assert byid['t20251103_114425']['quantity']==61
assert byid['t20251103_114425']['scope_assessment']=='范围细节需补充确认'
assert '11月31日' in byid['t20251103_114425']['scope_details']['status']
assert len([r for r in rows if r['retrieved_date']=='2026-10-20'])==44
