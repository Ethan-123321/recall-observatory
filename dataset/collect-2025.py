"""Collect the public 2025 catalogue using the same GET endpoint as the official site.
Caches responses, checks pagination counts, and keeps unreviewed records separate.
"""
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import urlencode, urljoin
from html.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor
import json, re, hashlib, time, collections, sys

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'raw' / 'annual-2025'
RAW.mkdir(parents=True, exist_ok=True)
BASE = 'https://www.samrdprc.org.cn'
ENTRY = BASE + '/fzlm/zhgg/xfpzhgg/index.html'
ASOF = '2026-10-21'

def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

def fetch(url, path):
    if path.exists():
        return path.read_bytes()
    # Sequential catalogue and at most three concurrent detail requests.
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={'User-Agent': 'RecallCourseResearch/1.0'}), timeout=35) as r:
                if r.status != 200:
                    raise ValueError(f'HTTP {r.status}')
                content = r.read()
            path.write_bytes(content)
            time.sleep(.3)
            return content
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2)

class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta = {}
        self.cells = []
        self.cell = None
        self.skip = 0
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'meta':
            self.meta[a.get('name', '')] = a.get('content', '')
        if tag in ('script', 'style'):
            self.skip += 1
        if tag in ('td', 'th'):
            self.cell = []
        if tag in ('br', 'p') and self.cell is not None:
            self.cell.append('\n')
    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.skip = max(0, self.skip - 1)
        if tag in ('td', 'th') and self.cell is not None:
            self.cells.append(re.sub(r'\s+', ' ', ''.join(self.cell)).strip())
            self.cell = None
    def handle_data(self, data):
        if self.cell is not None and not self.skip:
            self.cell.append(data)

def get_catalogue():
    entry = fetch(ENTRY, RAW / 'entry.html').decode('utf-8')
    query = json.loads(re.search(r'queryData="([^"]+)"', entry)[1].replace("'", '"'))
    api = urljoin(BASE, re.search(r'url="([^"]+)" queryData=', entry)[1])
    records, pages = [], []
    page_no, total = 1, None
    while total is None or len(records) < total:
        query['paramJson'] = json.dumps({
            'pageNo': page_no, 'pageSize': 15,
            'search': json.dumps({'deployTime': '2025-01-01 - 2025-12-31'})
        })
        url = api + '?' + urlencode(query)
        path = RAW / f'list-{page_no:03}.json'
        content = fetch(url, path)
        payload = json.loads(content)
        assert payload['success'], payload.get('message')
        html = payload['data']['html']
        params = json.loads(re.search(r'class="pagination" queryData="([^"]+)"', html)[1].replace("'", '"'))
        n = int(params['count'])
        assert total is None or total == n, 'Catalogue changed during collection; start a fresh snapshot'
        total = n
        found = re.findall(r'<li><a href="([^"]+)" title="([^"]*)"[^>]*>.*?<span>(\d{4}-\d{2}-\d{2})</span></li>', html, re.S)
        assert found, f'Empty page {page_no}'
        assert len(found) == min(15, total - len(records)), 'Incomplete pagination'
        for href, title, date in found:
            assert date.startswith('2025-'), 'Year filter was not applied'
            records.append({'source_url': urljoin(BASE, href), 'title': title, 'published_date': date, 'catalogue_page': page_no})
        pages.append({'page': page_no, 'count': len(found), 'source_url': url, 'raw_file': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(content).hexdigest()})
        print(f'catalogue {page_no}: {len(records)}/{total}', flush=True)
        page_no += 1
    assert len({r['source_url'] for r in records}) == total, 'Repeated page or duplicate URL'
    dump(ROOT / 'catalogue-2025.json', {'retrieved_date': ASOF, 'official_list_total': total, 'pages': pages, 'records': records})
    return records, pages, total

FIELD_NAMES = {
    '生产者名称': 'producer', '产品名称': 'product_name', '品牌': 'brand',
    '型号/规格': 'model_raw', '生产起止日期': 'production_dates_raw',
    '涉及数量': 'quantity_raw', '生产批号/批次': 'batch_raw',
    '存在的缺陷': 'defect_raw', '存在缺陷': 'defect_raw',
    '可能导致的后果': 'consequence_raw', '具体召回措施': 'remedy_raw',
    '避免损害发生的应急处置方式': 'emergency_raw',
}

def detail(record):
    row = dict(record)
    row['id'] = record['source_url'].rsplit('/', 1)[-1].removesuffix('.html')
    row['retrieved_date'] = ASOF
    row['review_status'] = '待逐条语义复核'
    row['automated_match_enabled'] = False
    path = RAW / (row['id'] + '.html')
    try:
        content = fetch(record['source_url'], path)
        parsed = Page()
        parsed.feed(content.decode('utf-8'))
        assert parsed.meta.get('ArticleTitle') == row['title'], 'Detail title does not match catalogue'
        row['raw_file'] = str(path.relative_to(ROOT))
        row['sha256'] = hashlib.sha256(content).hexdigest()
        row['detail_published_date'] = parsed.meta.get('DeployTime', '')[:10]
        row['metadata_pubdate'] = parsed.meta.get('PubDate', '')
        row['source_organization'] = parsed.meta.get('ContentSource', '')
        fields = {}
        for i, cell in enumerate(parsed.cells[:-1]):
            key = re.sub(r'\s+', '', cell).replace('／', '/')
            field = FIELD_NAMES.get(key)
            if not field and key.startswith('涉及数量（'):
                field = 'quantity_raw'
            if field:
                fields[field] = parsed.cells[i+1]
        row.update(fields)
        row['quality_flags'] = []
        if row['detail_published_date'] != row['published_date']:
            row['quality_flags'].append('列表与正文发布日期不一致')
        required = ['producer', 'product_name', 'model_raw', 'production_dates_raw', 'defect_raw', 'consequence_raw', 'remedy_raw']
        missing = [f for f in required if not fields.get(f) or fields[f] in ('/', '／', '无', '--')]
        row['missing_fields'] = missing
        row['extraction_status'] = '正文已提取' if not missing else '正文已下载·字段待补核'
    except Exception as e:
        row['extraction_status'] = '正文获取失败'
        row['error'] = str(e)
    return row

def main():
    rows, pages, total = get_catalogue()
    results = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        for row in pool.map(detail, rows):
            results.append(row)
            if len(results) % 30 == 0:
                print(f'detail {len(results)}/{total}', flush=True)
    existing = json.loads((ROOT / 'recalls.json').read_text(encoding='utf-8'))
    # Only exact title + publication date identities; preserve legacy source aliases.
    identities = collections.defaultdict(list)
    for old in existing:
        identities[(old['title'], old['published_date'])].append(old['id'])
    for row in results:
        row['existing_reviewed_ids'] = identities.get((row['title'], row['published_date']), [])
    months = []
    for i in range(1, 13):
        month = f'2025-{i:02}'
        subset = [r for r in results if r['published_date'].startswith(month)]
        months.append({
            'month': month, 'listed': len(subset),
            'downloaded': sum('sha256' in r for r in subset),
            'structured': sum(r['extraction_status'] == '正文已提取' for r in subset),
            'matched_reviewed': sum(bool(r['existing_reviewed_ids']) for r in subset),
        })
    result = {
        'year': 2025, 'retrieved_date': ASOF,
        'source_name': '市场监管总局召回中心·消费品召回公告栏目',
        'source_url': ENTRY, 'official_list_total': total,
        'catalogue_count': len(results), 'list_page_count': len(pages),
        'catalogue_complete': len(results) == total,
        'national': {
            'recall_events': 1081, 'products_ten_thousand': 823.6,
            'event_change_percent': -1.7, 'quantity_change_percent': 81.3,
            'source_url': 'https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/zlfzs/art/2026/art_a4a1efff07594041879134480a4aba4b.html',
            'published_date': '2026-03-19',
            'note': '全国实施召回次数，不等同于本栏目公告条数，不能用两者相除计算采集覆盖率。',
        },
        'months': months, 'records': results,
        'limitations': [
            '完整指采集日官方栏目年度查询返回的目录已遍历，不代表全国全部召回事件。',
            '按栏目发布日期统计公告，扩大召回与更正公告尚未完成事件级合并。',
            '新正文为规则提取，分类、风险与复杂范围尚待逐条语义复核；不进入已复核样本分析。',
            '网站迁移后的PubDate可能是迁移时间，年度统计使用目录日期并与DeployTime交叉核对。',
        ],
    }
    dump(ROOT / 'annual-2025.json', result)
    (ROOT.parent / 'dist' / 'annual-2025.js').write_text('const recallAnnual2025 = '+json.dumps(result, ensure_ascii=False)+';\n', encoding='utf-8')
    print(json.dumps({'total': total, 'status': dict(collections.Counter(r['extraction_status'] for r in results)), 'months': months}, ensure_ascii=False), flush=True)

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
