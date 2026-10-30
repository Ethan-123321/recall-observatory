"""Source-bound review integration. Never promotes OCR or keyword rules to review."""
from pathlib import Path
import json, hashlib, re, collections

ROOT = Path(__file__).resolve().parent
QUEUE_HASH = 'c21c4707c21b2444177bb29bf2c852f06027a25cc9a8d6a82943333e1873bdd1'
DAY = '2026-10-23'
METHOD = 'Codex AI辅助逐条复核，非人工专家认证'
FIELDS = ['producer','product_name','brand','model_raw','production_dates_raw','batch_raw',
          'quantity_raw','quantity','quantity_unit','defect_raw','consequence_raw','remedy_raw']

def load(name):
    return json.loads((ROOT/name).read_text(encoding='utf-8-sig'))

def norm(value):
    return re.sub(r'\s+', '', value or '')

def source_ok(r):
    path = (ROOT/r['raw_file']).resolve()
    assert path.is_relative_to(ROOT), r['id']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == r['sha256'], r['id']

def decisions():
    assert hashlib.sha256((ROOT/'semantic-review-queue.json').read_bytes()).hexdigest() == QUEUE_HASH, 'Fixed queue changed'
    queue = load('semantic-review-queue.json')
    data = load('semantic-decisions-2023-2025.json')
    assert len(queue) == len(data['decisions']) == 764
    assert set(data['decisions']) == {str(i) for i in range(764)}
    out = {}
    for i, r in enumerate(queue):
        d = data['decisions'][str(i)]
        assert d['id'] == r['id'] and d['source_sha256'] == r['sha256']
        source_ok(r)
        assert norm(d['risk_evidence']) == norm((r.get('defect_raw') or '') + (r.get('consequence_raw') or '')), r['id']
        assert d['category'] and d['category_evidence'] and d['review_dimensions'] == ['category','risk']
        assert d['risks'] and len(set(d['risks'])) == len(d['risks'])
        assert all(c in data['risk_codes'] for c in d['risks'])
        out[r['id']] = {**d, 'risk_tags':[data['risk_codes'][c] for c in d['risks']], 'queue_index':i}
    return out

def apply(rows, excluded):
    ds = decisions()
    scopes = load('scope-decisions-2023-2025.json')
    assert set(scopes)==set(ds)
    overrides = load('semantic-corrections-2023-2025.json') if (ROOT/'semantic-corrections-2023-2025.json').exists() else {}
    for r in rows:
        source_ok(r)
        if r['id'] in ds:
            d = ds[r['id']]
            if r['id'] in overrides:
                fix = overrides[r['id']]
                assert fix['source_sha256'] == r['sha256']
                d = {**d, **fix}
            r.update(category=d['category'], risk_tags=d['risk_tags'],
                     risk_evidence={t:[d['risk_evidence']] for t in d['risk_tags']},
                     category_method=METHOD+'：按产品用途及公告标题判定',
                     risk_method=METHOD+'：仅依据缺陷和后果段落编码',
                     review_status='分类与风险已AI辅助复核·范围待复核')
            r['semantic_review'] = d
            r['review_stages'] = dict(category='AI辅助复核完成',risk='AI辅助复核完成',scope='待逐字段复核',transcription='不适用：HTML文本')
            r['quality_flags'] = [x for x in r.get('quality_flags',[]) if '规则辅助编码' not in x]
            r['quality_flags'].append('本次语义复核仅覆盖分类、风险；范围提取不能冒充逐字段复核。')
            s=scopes[r['id']]
            assert s['source_sha256']==r['sha256'] and s['queue_index']==d['queue_index']
            r['scope_original_fields']={k:r.get(k) for k in s['fields']}
            r.update(s['fields'])
            r['source_fields'].update(s['fields'])
            r['scope_review']=s
            r['scope_details']=s['scope_details']
            r['review_stages']['scope']=s['status']
            if s.get('images'):r['review_stages']['transcription']='范围型号表AI视觉核对·非全文转录'
            r['review_status']='分类、风险及范围条件已AI辅助复核'+('·含待确认项' if '部分' in s['status'] else '')
            r['scope_reviewed_at']=DAY
            r['batch_review_note']=s['note']
            r['quality_flags']=[s['note'],'范围字段复核不表示全部公告字段已复核；AI辅助核对不是厂家确认。']
            r['field_review']={k:dict(status=s['status'],evidence=s['fields'].get(k),source_sha256=r['sha256']) for k in s['review_dimensions']}
        elif r['domain'] == '食品':
            r['review_stages'] = dict(category='AI辅助复核完成',risk='AI辅助复核完成',scope='关键字段AI视觉核对',transcription='关键字段AI视觉核对')
        else:
            r['review_stages'] = dict(category='既有AI辅助文本复核',risk='既有AI辅助文本复核',scope='既有AI辅助文本复核',transcription='不适用：HTML文本')
    backlog = load('backlog-source-2023-2025.json')
    ledger = load('backlog-decisions-2023-2025.json')
    assert set(ledger) == {r['id'] for r in backlog}
    removed = set()
    by_id = {r['id']:r for r in rows}
    for src in backlog:
        source_ok(src)
        d = ledger[src['id']]
        assert d['source_sha256'] == src['sha256']
        if d['disposition'] != 'include':
            continue
        assert d['fields'].get('product_name') and d['fields'].get('defect_raw') and d['category'] and d['risk_tags']
        r = {**src, **d['fields']}
        for field in FIELDS:
            r.setdefault(field, None)
        r.update(domain=d['domain'],year=src['published_date'][:4],category=d['category'],risk_tags=d['risk_tags'],
                 source_fields=d['fields'].copy(),source_text=d['source_text'],risk_evidence=d['risk_evidence'],
                 source_coverage='福建省食品召回栏目有限样本' if d['domain']=='食品' else '召回中心'+('汽车' if d['domain']=='汽车' else '消费品')+'栏目',
                 category_method=METHOD,risk_method=METHOD,review_status='积压公告关键字段已AI辅助复核',
                 extraction_status=d['method'],review_stages=d['review_stages'],field_review=d['field_review'],
                 automated_match_enabled=False,analysis_eligible=True,quality_flags=d['uncertainties'],
                 source_missing_fields=[f for f in FIELDS if r.get(f) is None],
                 scope_assessment='范围细节需补充确认',scope_reviewed_at=DAY,
                 batch_review_note=d['scope_note'],review_provenance=d)
        if r['id'] in by_id:
            rows[rows.index(by_id[r['id']])] = r
        else:
            rows.append(r)
        removed.add(r['id'])
    for r in rows:
        r.setdefault('scope_assessment_reason',r.get('batch_review_note') or '按公告限定的型号、日期和批次核对；实际产品需厂家确认。')
        r.setdefault('emergency_raw',None)
        r.setdefault('contact_raw',None)
        if 'partial' in str(r.get('review_stages',{})) or any('部分' in v for v in r.get('review_stages',{}).values()):
            r['review_status']+='·存在未确认字段' if '待确认' not in r['review_status'] else ''
        if r['domain']=='食品':
            r['risk_evidence']={t:[r['defect_raw']] for t in r['risk_tags']}
    remaining = []
    for src in backlog:
        d = ledger[src['id']]
        if src['id'] not in removed:
            remaining.append({**src,'exclude_reason':d['reason'],'review_stages':d['review_stages'],
                              'review_disposition':d['disposition'],'review_evidence':d})
    return rows, remaining

def quality(rows):
    ledger = load('backlog-decisions-2023-2025.json')
    return {
        'review_stages': {stage:dict(collections.Counter(r['review_stages'][stage] for r in rows))
                          for stage in ['category','risk','scope','transcription']},
        'backlog_dispositions':dict(collections.Counter(d['disposition'] for d in ledger.values())),
        'backlog_review_stages':{s:dict(collections.Counter(d['review_stages'][s] for d in ledger.values())) for s in ['category','risk','scope','transcription']},
        'fixed_queue_sha256':QUEUE_HASH,
        'semantic_decisions_validated':len(decisions()),
        'by_domain_year':{domain:dict(collections.Counter(r['year'] for r in rows if r['domain']==domain)) for domain in sorted({r['domain'] for r in rows})},
        'review_notice':'AI辅助复核不是人工专家认证；各阶段分别记录，未完成范围复核不能自动判断实际产品命中。'
    }
