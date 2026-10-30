"""Materialize explicit AI visual review notes; does not classify from OCR."""
from pathlib import Path
import json, hashlib, re
ROOT=Path(__file__).resolve().parent
load=lambda n:json.loads((ROOT/n).read_text(encoding='utf-8-sig'))
dump=lambda n,v:(ROOT/n).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
sources=load('backlog-source-2023-2025.json')
images=load('review-image-ledger.json')
codes=load('semantic-decisions-2023-2025.json')['risk_codes']
ledger=load('backlog-decisions-2023-2025.json') if (ROOT/'backlog-decisions-2023-2025.json').exists() else {}
for r in sources:
    if r['id'] in ledger:continue
    refs=[x for x in images if x['id']==r['id']]
    ocr=[]
    for x in refs:
        f=ROOT/'ocr-review'/(Path(x['file']).name+'.json')
        if f.exists():
            value=json.loads(f.read_text(encoding='utf-8-sig'))
            assert value['sha256']==x['sha256']==hashlib.sha256((ROOT/x['file']).read_bytes()).hexdigest()
            ocr.append(dict(file=str(f.relative_to(ROOT)),sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
    ledger[r['id']]=dict(source_sha256=r['sha256'],disposition='pending',reason='本地OCR已取得，待原图逐字段核对' if ocr else '待原文逐字段核对',
        images=[{k:x[k] for k in ['file','sha256','source_url']} for x in refs],ocr=ocr,
        review_stages=dict(category='待复核',risk='待复核',scope='待复核',transcription='本地OCR完成·未复核' if ocr else '待处理'),
        method='Windows本地中文OCR；不使用云端或付费API')
notes=ROOT/'backlog-reviewed.tsv'
if notes.exists():
    for line in notes.read_text(encoding='utf-8').splitlines():
        if not line.strip() or line.startswith('#'):continue
        cols=line.split('|')
        assert len(cols)==12, (len(cols),line)
        idx,cat,risk,product,model,dates,batch,qty,defect,consequence,remedy,note=cols
        src=sources[int(idx)];d=ledger[src['id']]
        assert d['images'],src['id']
        fields=dict(product_name=product,producer=re.sub('主动$','',src['title'].split('召回')[0]),brand=None,model_raw=model or None,
                    production_dates_raw=dates or None,batch_raw=batch or None,quantity_raw=qty or None,
                    defect_raw=defect,consequence_raw=consequence or None,remedy_raw=remedy or None)
        m=re.fullmatch(r'([0-9,，]+)(个|件|台|只|套|辆|双|包|袋|本|盒|支|组|瓶|枚|把)',qty)
        fields.update(quantity=int(m[1].replace(',','').replace('，','')) if m else None,quantity_unit=m[2] if m else None)
        partial=bool(re.search('待核|待确认|不易区分|疑似|尚未|无法辨认|倒置',note))
        d.update(disposition='include',reason='逐条读取本地OCR并对照原图关键字段',domain='一般消费品',category=cat,
                 risk_tags=[codes[c] for c in risk],fields=fields,method='Windows本地OCR + Codex原图逐字段核对（非人工专家认证）',
                 reviewer='Codex',reviewed_at='2026-10-23',uncertainties=[note] if note else [],
                 source_text='\n'.join(k+'：'+str(v) for k,v in fields.items() if v is not None),
                 risk_evidence={codes[c]:[defect,consequence] for c in risk},
                 field_review={k:{'status':'原图关键字段AI核对' if v is not None else '原图未明确披露或无法可靠辨认，保留缺失',
                                  'evidence':v,'sources':[x['file'] for x in d['images']]} for k,v in fields.items()},
                 review_stages=dict(category='AI辅助复核完成',risk='AI辅助复核完成',scope='关键字段部分核对·存在待确认项' if partial else '关键字段AI视觉核对',transcription='关键字段部分核对·存在待确认项' if partial else '关键字段AI视觉核对'),
                 scope_note='按公告型号、生产日期及批次共同确认；原文分组及离散日期保留。批次数量不等于批次编号，空白或“/”不代表全部批次；不自动判断具体产品命中。'+note)
        d['evidence_notice']='fields为原图关键字段摘录或摘要；未声称全文逐字转录。OCR为未经逐字校订的辅助文本，原始图片及哈希是依据。生产者另参考公告标题。'
        d['field_review']['producer']['status']='公告标题与原图主体参考'
        d['field_review']['brand']['status']='本次未独立转录品牌字段；不表示原文未披露'
        if int(idx)==31:
            d['uncertain_candidates']={'model_raw':model}
            d['fields']['model_raw']=None
            d['field_review']['model_raw']['status']='字符0/O、1/I无法可靠区分，候选文字仅供原图查证，不作确定型号'
        if int(idx)==115:
            d['fields']['product_name']='王牌赛车大联盟玩具'
            d['field_review']['product_name'].update(status='采用官方公告标题产品名；原图名称未清晰转录',evidence=src['title'])
        d['source_text']='\n'.join(k+'：'+str(v) for k,v in d['fields'].items() if v is not None)
dump('backlog-decisions-2023-2025.json',ledger)
