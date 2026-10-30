"""Check yearly catalogue coverage, saved evidence and front-end consistency."""
from pathlib import Path
import json, hashlib, collections, re, sys

sys.stdout.reconfigure(encoding='utf-8')
root = Path(__file__).resolve().parent
annual = json.loads((root / 'annual-2025.json').read_text(encoding='utf-8'))
catalogue = json.loads((root / 'catalogue-2025.json').read_text(encoding='utf-8'))
rows = annual['records']
assert len(rows) == annual['official_list_total'] == catalogue['official_list_total']
assert len({r['source_url'] for r in rows}) == len(rows)
assert len({r['id'] for r in rows}) == len(rows)
assert all(r['published_date'].startswith('2025-') for r in rows)
assert all(r['automated_match_enabled'] is False for r in rows)
assert all(r['review_status'] == '待逐条语义复核' for r in rows)

listed = []
for i, page in enumerate(catalogue['pages'], 1):
    assert page['page'] == i
    content = (root / page['raw_file']).read_bytes()
    assert hashlib.sha256(content).hexdigest() == page['sha256']
    html = json.loads(content)['data']['html']
    matches = re.findall(r'<li><a href="([^"]+)" title="([^"]*)"[^>]*>.*?<span>(\d{4}-\d{2}-\d{2})</span></li>', html, re.S)
    assert len(matches) == page['count']
    listed.extend(('https://www.samrdprc.org.cn'+href, title, date) for href,title,date in matches)
assert listed == [(r['source_url'], r['title'], r['published_date']) for r in rows]
for row in rows:
    if row.get('sha256'):
        content = (root / row['raw_file']).read_bytes()
        assert hashlib.sha256(content).hexdigest() == row['sha256']
    if row['extraction_status'] == '正文已提取':
        assert not row['missing_fields']

assert [m['month'] for m in annual['months']] == [f'2025-{i:02}' for i in range(1,13)]
for month in annual['months']:
    subset = [r for r in rows if r['published_date'].startswith(month['month'])]
    assert month['listed'] == len(subset)
    assert month['downloaded'] == sum(bool(r.get('sha256')) for r in subset)
    assert month['structured'] == sum(r['extraction_status']=='正文已提取' for r in subset)
    assert month['matched_reviewed'] == sum(bool(r['existing_reviewed_ids']) for r in subset)
    assert 0 <= month['structured'] <= month['downloaded'] <= month['listed']
assert sum(m['listed'] for m in annual['months']) == len(rows)
js = (root.parent / 'dist' / 'annual-2025.js').read_text(encoding='utf-8')
assert json.loads(js.removeprefix('const recallAnnual2025 = ').strip().removesuffix(';')) == annual
# The first notice migrated in 2026 but was published in 2025.
first = rows[0]
assert first['published_date'] == first['detail_published_date'] == '2025-12-31'
assert first['product_name'] == '面巾' and first['quantity_raw'] == '86500条'
assert first['metadata_pubdate'].startswith('2026-')
print(f"PASS: {len(rows)} unique 2025 entries, {len(catalogue['pages'])} complete list pages, 12 monthly totals, raw hashes, extraction states, migration date and frontend consistency.")
print(collections.Counter(r['extraction_status'] for r in rows))
