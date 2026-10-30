"""Cross-check original evidence, explicit decisions, exports and analysis invariants."""
from pathlib import Path
import json,hashlib,collections,sqlite3,runpy,sys
ROOT=Path(__file__).resolve().parent
sys.stdout.reconfigure(encoding='utf-8')
def read(n):return json.loads((ROOT/n).read_text(encoding='utf-8'))
a=read('annual-2025-reviewed.json');old=read('annual-2025.json');rows=read('recalls-2025-reviewed.json');ledger=read('review-ledger-2025.json');report=read('quality-report-2025.json')
assert len(a['records'])==len(ledger)==342 and len(rows)==341
assert len({r['id'] for r in rows})==341
parser=runpy.run_path(str(ROOT/'collect-2025.py'),run_name='verify_import')
for index,(source,row,review) in enumerate(zip(old['records'],a['records'],ledger)):
    assert source['id']==row['id']==review['id']
    raw=(ROOT/row['raw_file']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==row['sha256']==source['sha256']
    assert row['review_status']=='已完成AI辅助文本复核'
    assert row['automated_match_enabled'] is False
    assert row['category'] and len(row['risk_tags'])==len(set(row['risk_tags']))>0
    assert row['published_date']==row['detail_published_date'] and row['published_date'].startswith('2025-')
    if index not in (5,324):
        parsed=parser['detail']({k:source[k] for k in ['source_url','title','published_date','catalogue_page']})
        for key in ['producer','product_name','model_raw','production_dates_raw','batch_raw','defect_raw','consequence_raw','remedy_raw','quantity_raw']:
            assert row['source_fields'].get(key)==parsed.get(key),(index,key)
    else:
        img=row['image_evidence'];assert hashlib.sha256((ROOT/img['file']).read_bytes()).hexdigest()==img['sha256']
    for key in ['defect_raw','consequence_raw','production_dates_raw','remedy_raw']:
        assert row.get(key),(index,key)
    assert row['quantity'] is None or row['quantity']>=0
assert a['records'][108]['product_name']=='背包'
assert a['records'][213]['product_name']=='音乐玩具'
assert a['records'][329]['duplicate_of']==a['records'][327]['id']
assert a['records'][143]['scope_assessment']=='范围细节需补充确认'
assert a['records'][269]['model_raw']=='请详附件'
assert a['records'][291]['scope_assessment']=='明确限定范围内全部批次'
assert len(a['records'][319]['scope_details']['groups'])==4
assert sum(m['analysis_count'] for m in a['months'])==341
assert sum(m['listed'] for m in a['months'])==342
assert sum(report['category_counts'].values())==341
assert report['risk_counts']==dict(collections.Counter(t for r in rows for t in r['risk_tags']))
for filename,prefix,data in [('annual-2025-reviewed.js','const recallAnnual2025 = ',a),('dataset-2025.js','const recallDataset = ',rows)]:
    js=(ROOT.parent/'dist'/filename).read_text(encoding='utf-8');assert json.loads(js.removeprefix(prefix).strip().removesuffix(';'))==data
with sqlite3.connect(ROOT/'recalls-2025.sqlite3') as db:
    saved={i:json.loads(v) for i,v in db.execute('SELECT id,record_json FROM notices')}
    assert saved=={r['id']:r for r in rows}
print('PASS: 342 source reviews, 340 HTML field comparisons, 2 image hashes, 341 unique records, month/category/risk totals, complex scopes, SQLite and browser exports.')
