from pathlib import Path
import json,hashlib,sqlite3,csv,sys,importlib.util,collections,os,re
os.environ['RECALL_SKIP_ENV']='1'
os.environ['RECALL_OFFLINE']='1'
ROOT=Path(__file__).resolve().parent
rows=json.loads((ROOT/'recalls-2023-2025.json').read_text(encoding='utf-8'))
assert len(rows)>=1000 and len({r['id'] for r in rows})==len(rows)
for r in rows:
 assert r['year'] in ['2023','2024','2025'] and r['published_date'].startswith(r['year'])
 assert hashlib.sha256((ROOT/r['raw_file']).read_bytes()).hexdigest()==r['sha256']
 assert r['source_url'].startswith('https://') and r['category'] and r['risk_tags'] and r['defect_raw']
 assert r['automated_match_enabled'] is False
 assert r['domain'] in ['一般消费品','汽车','食品']
 assert r['domain']!='食品' or r['source_url'].startswith('https://scjgj.fujian.gov.cn/')
with sqlite3.connect(ROOT/'recalls-2023-2025.sqlite3') as db:assert [json.loads(x[0]) for x in db.execute('select record_json from notices')]==rows
with (ROOT/'recalls-2023-2025.csv').open(encoding='utf-8-sig',newline='') as f:
 exported=list(csv.DictReader(f));assert [json.loads(x['record_json']) for x in exported]==rows
 for c,r in zip(exported,rows):
  for k in ['id','producer','model_raw','production_dates_raw','batch_raw','quantity_raw','defect_raw','consequence_raw','remedy_raw','source_url','sha256']:
   assert c[k]==str(r.get(k) or ''),(r['id'],k)
js=(ROOT.parent/'dist/dataset-multidomain.js').read_text(encoding='utf-8');assert json.loads(js.split(' = ',1)[1].split(';\nconst recallCoverage')[0])==rows
spec=importlib.util.spec_from_file_location('server',ROOT.parent/'server.py');server=importlib.util.module_from_spec(spec);spec.loader.exec_module(server)
for domain in ['全部','一般消费品','汽车','食品']:
 for year in ['全部','2023','2024','2025']:
  found=server.select(server.validate({'domain':domain,'year':year}))
  expected=[r for r in rows if (domain=='全部' or r['domain']==domain) and (year=='全部' or r['year']==year)]
  assert found==expected
report=json.loads((ROOT/'quality-multidomain.json').read_text(encoding='utf-8'))
assert report['count']==len(rows) and report['by_domain']==dict(collections.Counter(r['domain'] for r in rows))
assert report['by_year']==dict(collections.Counter(r['year'] for r in rows))
for s in ['category','risk','scope','transcription']:assert report['review_stages'][s]==dict(collections.Counter(r['review_stages'][s] for r in rows))
import review_pipeline
decisions=review_pipeline.decisions();assert len(decisions)==764
queue=json.loads((ROOT/'semantic-review-queue.json').read_text(encoding='utf-8'))
by={r['id']:r for r in rows}
for x in json.loads((ROOT/'review-image-ledger.json').read_text(encoding='utf-8'))+json.loads((ROOT/'scope-image-ledger.json').read_text(encoding='utf-8')):
 assert hashlib.sha256((ROOT/x['file']).read_bytes()).hexdigest()==x['sha256']
 o=ROOT/'ocr-review'/(Path(x['file']).name+'.json')
 assert o.exists() and json.loads(o.read_text(encoding='utf-8-sig'))['sha256']==x['sha256']
for i,r in enumerate(queue):
 d=by[r['id']];s=d['scope_review']
 assert s['source_sha256']==r['sha256'] and s['queue_index']==i
 if r['domain']=='一般消费品':
  for k in ['model_raw','production_dates_raw','batch_raw','quantity_raw']:
   assert i==499 or d[k]==r['source_fields'].get(k),(i,k)
 else:
  assert s['evidence'] and all(g['evidence'] in d['source_text'] for g in s['scope_details']['groups'])
 assert d['review_stages']['scope']!='待逐字段复核'
assert by[queue[70]['id']]['quantity']==138 and by[queue[70]['id']]['quantity_unit']=='件'
assert '车辆失控' not in by[queue[381]['id']]['risk_tags']
assert by[queue[380]['id']]['risk_tags']==['乘员保护失效']
assert by[queue[382]['id']]['risk_tags']==['触电']
assert by[queue[499]['id']]['model_raw'].count('；')==15
assert by[queue[158]['id']]['production_dates_raw']=='2021年11月3日至2011年11月4日'
assert '需厂家确认' in by[queue[158]['id']]['review_stages']['scope']
assert by[queue[316]['id']]['category']==by[queue[624]['id']]['category']=='玩具'
assert by[queue[540]['id']]['category']=='家具家居'
assert by[queue[31]['id']]['quantity'] is None
backlog=review_pipeline.load('backlog-source-2023-2025.json');ledger=review_pipeline.load('backlog-decisions-2023-2025.json')
assert len(backlog)==len(ledger)==200 and collections.Counter(d['disposition'] for d in ledger.values())=={'include':199,'out_of_scope_summary':1}
for src in backlog:
 d=ledger[src['id']];assert d['source_sha256']==src['sha256']
 if d['disposition']=='include':
  assert src['id'] in by and by[src['id']]['review_provenance']==d
  assert not by[src['id']].get('quantity_unit') or by[src['id']]['quantity_unit'] in ['个','件','台','只','套','辆','双','包','袋','本','盒','支','组','瓶','枚','把']
for src in backlog[195:199]:assert by[src['id']]['production_dates_raw'] and 'VIN' in by[src['id']]['batch_review_note']
assert by[backlog[195]['id']]['quantity'] is None and len(by[backlog[195]['id']]['scope_details']['groups'])==2
assert by[backlog[198]['id']]['quantity'] is None and len(by[backlog[198]['id']]['scope_details']['groups'])==2
assert by[backlog[31]['id']]['model_raw'] is None
assert by[backlog[78]['id']]['batch_raw'].count('、')==9
assert '邻苯二甲酸二抽检不合格' in by[backlog[199]['id']]['defect_raw']
assert report['by_domain_year']['食品']=={'2025':5}
for filters in ([{'category':x} for x in server.CATS]+[{'risk':x} for x in server.RISKS]+[{'query':x} for x in ['TRW','JTC 1619','X5','ZURUDG','20250907','PA-1900','不存在的商品X987']]):
 f=server.validate(filters);found=server.select(f)
 with __import__('unittest.mock',fromlist=['patch']).patch.object(server,'configured',return_value=False):
  result=server.analyze('什么风险最多',f);assert result['facts']['count']==len(found)
  if found:assert server.analyze('解释这条公告',f,found[0]['id'])['evidence']
sys.stdout.reconfigure(encoding='utf-8');print('PASS: hashes, immutable 764 queue, 200 dispositions, source scope evidence, regression fields/risks, export parity, all category/risk filters, 16 domain/year filters, assistant counts:',len(rows))
