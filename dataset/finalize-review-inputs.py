"""Explicit corrections after comparing individual source evidence. No API calls."""
from pathlib import Path
import json, re, runpy
ROOT=Path(__file__).resolve().parent
load=lambda n:json.loads((ROOT/n).read_text(encoding='utf-8-sig'))
def dump(n,v): (ROOT/n).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
notes=ROOT/'backlog-reviewed.tsv'
lines=[]
for line in notes.read_text(encoding='utf-8').splitlines():
    if not line or line.startswith('#'): lines.append(line); continue
    a=line.split('|'); i=int(a[0])
    if i==0:
        a[8]=a[8].replace('吸光材料','反光材料');a[11]='生产日期与批号文字不同，按原图分别保留。'
    if i==78:
        a[3]='宝贝小鲨鱼玩具'
        a[6]='、'.join('ZURUDG'+v+'CHINA' for v in ['20191223','20200409','20200401','20200601','20200619','20201019','20210325','20210426','20210604','20211115'])
        a[11]='10个离散批号分别保留，不扩大为连续生产区间。'
    if i==173:
        a[6]='卡迪之光：JDSCRK00000066、JDSCRK00000026、JDSCRK00000088、JDSCRK00000101；米兰极光：JDSCRK00000020、JDSCRK00000077、JDSCRK00000156、JDSCRK00000214、JDSCRK00000712、JDSCRK00001420'
        a[10]='停止使用，为消费者免费办理退货。';a[11]='两个型号与各自批号对应保存，共10个离散批号，不展开为连续范围。'
    lines.append('|'.join(a))
assert len(lines)-1==194 and len({int(x.split('|')[0]) for x in lines if x and not x.startswith('#')})==194
notes.write_text('\n'.join(lines)+'\n',encoding='utf-8')
runpy.run_path(str(ROOT/'prepare-backlog-review.py'))
q=load('semantic-review-queue.json'); old=load('semantic-decisions-2023-2025.json');codes=old['risk_codes']
fixes={25:'p',48:'dvP',49:'dvP',50:'dvP',51:'dvP',375:'Vi',376:'o',378:'fle',379:'d',380:'p',381:'hfX',382:'E',383:'ci',384:'SmH',385:'Sm',386:'e',387:'pi',388:'lc',389:'c',390:'v',391:'vc',392:'o',393:'cvhfX',394:'E'}
out={}
for i,code in fixes.items():
    d=old['decisions'][str(i)];r=q[i]
    out[r['id']]=dict(source_sha256=r['sha256'],risk_tags=[codes[c] for c in code],
        risk_evidence=d['risk_evidence'],category=d['category'],original_risks=d['risks'],
        reason='重新对照本条缺陷及后果原文修正编码；375—394区段存在标签错位。碰撞保护失效与碰撞发生风险分开；热失控不是车辆失控；仅保留原文支持的风险。',
        reviewer='Codex AI辅助复核，非人工专家认证',reviewed_at='2026-10-23')
for i in [285,554]:
    d=old['decisions'][str(i)];r=q[i]
    out[r['id']]=dict(source_sha256=r['sha256'],risk_tags=['驾驶辅助功能异常'],risk_evidence=d['risk_evidence'],category=d['category'],original_risks=d['risks'],
        reason='原文为驾驶辅助/脱手检测功能异常，不能仅据此推断碰撞发生或视野异常。',reviewer='Codex AI辅助复核',reviewed_at='2026-10-23')
dump('semantic-corrections-2023-2025.json',out)
sources=load('backlog-source-2023-2025.json');ledger=load('backlog-decisions-2023-2025.json')
from html.parser import HTMLParser
class Text(HTMLParser):
    def __init__(self):super().__init__();self.active=0;self.parts=[];self.skip=0
    def handle_starttag(self,t,a):
        if dict(a).get('id')=='zoom':self.active=1;return
        if self.active and t=='div':self.active+=1
        if self.active and t in ['style','script']:self.skip+=1
        if self.active and t in ['p','br','tr']:self.parts.append('\n')
    def handle_endtag(self,t):
        if self.active and t=='div':self.active-=1
        if t in ['style','script']:self.skip=max(0,self.skip-1)
    def handle_data(self,s):
        if self.active and not self.skip:self.parts.append(s)
    def text(self):return '\n'.join(re.sub(r'\s+',' ',s).strip() for s in ''.join(self.parts).splitlines() if s.strip())
def body(src):
    p=Text();p.feed((ROOT/src['raw_file']).read_text(encoding='utf-8'));return p.text()
def include(i,domain,fields,tags,note,groups=None):
    src=sources[i];d=ledger[src['id']]
    d.update(disposition='include',reason='逐条阅读全文并核对关键字段',domain=domain,category=domain,risk_tags=tags,fields=fields,
        method='Codex逐段HTML原文核对' if domain=='汽车' else 'Codex本地PDF渲染后原图关键字段核对',reviewer='Codex AI辅助复核，非人工专家认证',reviewed_at='2026-10-23',
        source_text=body(src) if domain=='汽车' else '\n'.join(str(v) for v in fields.values() if v is not None),
        risk_evidence={t:[fields['defect_raw']] for t in tags},uncertainties=[note],scope_note=note,
        review_stages=dict(category='AI辅助复核完成',risk='AI辅助复核完成',scope='关键字段AI文本核对' if domain=='汽车' else '关键字段AI视觉核对',transcription='不适用：HTML文本' if domain=='汽车' else '关键字段部分核对·原文项目名称不完整'))
    d['field_review']={k:dict(status='原文AI逐字段核对' if v is not None else '公告未明确披露，保留缺失',evidence=v,source=src['raw_file'],source_sha256=src['sha256']) for k,v in fields.items()}
    if groups: d['fields']['scope_details']=dict(status='按原文分别核对各组；不自动交叉配对，不累加数量',groups=groups)
def fields(product,producer,model,dates,qty,defect,remedy):
    m=re.fullmatch(r'([0-9,]+)(辆|件)',qty)
    return dict(product_name=product,producer=producer,brand=None,model_raw=model,production_dates_raw=dates,batch_raw=None,quantity_raw=qty,quantity=int(m[1].replace(',','')) if m else None,quantity_unit=m[2] if m else None,defect_raw=defect,consequence_raw=None,remedy_raw=remedy)
vin='汽车须按VIN向厂家确认；批次未披露不表示全部批次。'
include(195,'汽车',fields('大捷龙3.6L插电混合动力汽车','克莱斯勒（中国）汽车销售有限公司','进口大捷龙3.6L插电式混合动力','第一组：2017年8月21日至2017年9月12日；第二组：2019年2月15日至2019年10月18日','第一组711辆；第二组930辆','上述召回范围内部分车辆因动力电池内部故障，可能会发生潜在的源自动力电池内部的起火，进而导致车辆起火，存在安全隐患。','免费刷新动力电池控制模块软件，识别故障并更换有缺陷的动力电池。升级前避免充电，并将车辆停放在远离建筑物及其他车辆的区域。'),['火灾/燃烧'],vin+'两组实施起始日分别为2025-01-01、2025-03-01；分别属于再次召回和扩大召回。',[
dict(model='进口大捷龙3.6L插电式混合动力',source_dates='2017年8月21日至2017年9月12日',quantity_raw='711辆',recall_start='2025-01-01'),dict(model='进口大捷龙3.6L插电式混合动力',source_dates='2019年2月15日至2019年10月18日',quantity_raw='930辆',recall_start='2025-03-01')])
include(196,'汽车',fields('进口SOLTERRA汽车','斯巴鲁汽车（中国）有限公司','SOLTERRA','2023年4月26日','1辆','前视摄像头外壳焊接不良，雨水可能进入并导致内部电路板腐蚀、导通不良，无法正常显示车辆前方图像，增加车辆碰撞风险，存在安全隐患。','免费更换前视摄像头，并进行光轴校准。'),['视野/警示功能异常','碰撞/失控风险'],vin+'生产范围在第一段备案说明中，2023年4月26日为单个生产日期。')
include(197,'汽车',fields('进口DS 3纯电动汽车','标致雪铁龙（上海）管理有限公司','DS 3纯电动','2020年11月18日至2021年7月21日','49辆','空调压缩机绝缘性降低；车辆诊断软件检测到绝缘性降低可能切断动力电池主继电器，造成车辆行驶中动力中断，存在安全隐患。','免费升级车辆软件。'),['动力功能异常'],vin+'生产范围在第一段备案说明中；缺陷与免费升级写在同一段，不能整段丢弃。再次召回，原公告日期2022-09-16。')
include(198,'汽车',fields('路虎揽胜及捷豹I-PACE汽车','捷豹路虎（中国）投资有限公司','第一组：2022—2023款路虎揽胜；第二组：2019—2020款捷豹I-PACE','第一组：2021年11月29日至2022年11月28日；第二组：2018年4月11日至2020年7月17日','第一组6415辆；第二组995辆','第一组：尾灯线束可能被夹，导致尾灯不工作，增加碰撞风险。第二组：动力电池可能出现热过载，严重时可能起火。','第一组免费检查尾灯线束，必要时更换；第二组免费升级电池能量控制模块软件，出现相关警告后按规定检查并更换电池模组。'),['视野/警示功能异常','碰撞/失控风险','电池过热/热失控','火灾/燃烧'],vin+'两组缺陷、措施及数量分别对应，风险按公告联合展示，不表示两种车型均存在所有风险。',[
dict(model='2022—2023款路虎揽胜',source_dates='2021年11月29日至2022年11月28日',quantity_raw='6415辆',risk_tags=['视野/警示功能异常','碰撞/失控风险'],recall_start='2023-07-28'),dict(model='2019—2020款捷豹I-PACE',source_dates='2018年4月11日至2020年7月17日',quantity_raw='995辆',risk_tags=['电池过热/热失控','火灾/燃烧'],recall_start='立即')])
d=ledger[sources[194]['id']];d.update(disposition='out_of_scope_summary',reason='多企业召回汇总新闻，非独立召回公告；10家企业、56个车型、1675辆不能作为新的独立召回重复累计。',source_text=body(sources[194]),review_stages=dict(category='非独立公告：不适用',risk='非独立公告：不适用',scope='已核对汇总新闻性质',transcription='不适用：HTML文本'),method='Codex阅读全文核对',reviewed_at='2026-10-23')
f=dict(product_name='花生油',producer='南安市翔达油脂发展有限公司',brand='到您家',model_raw='5L',production_dates_raw='20250907',batch_raw=None,quantity_raw=None,quantity=None,quantity_unit=None,
    defect_raw='硬脂酸，花生酸，邻苯二甲酸二丁酯，邻苯二甲酸二抽检不合格，食用有损人体健康',consequence_raw='食用有损人体健康',remedy_raw='公告发布之日起20个工作日内实施二级召回；停止销售并主动召回，消费者可凭有效凭证退货、赔偿。',notice_signed_date='2025-10-09',sales_area='南安市康美镇')
include(199,'食品',f,['化学健康风险'],'原图项目“邻苯二甲酸二”文字不完整，原样保留，不能猜填化合物名称；生产日期（批次）为同一合并字段20250907，未另给独立批号。数量未披露。署名日期2025-10-09与目录发布日期2025-10-12分开保存。食品仅为福建有限样本。')
ledger[sources[199]['id']]['fields']['production_date_batch_raw']='生产日期（批次）：20250907'
ledger[sources[198]['id']]['fields']['remedy_raw']=ledger[sources[198]['id']]['fields']['remedy_raw'].replace('必要时更换','受损则免费更换尾灯')
dump('backlog-decisions-2023-2025.json',ledger)
print('Reviewed backlog:',len(ledger),'included:',sum(d['disposition']=='include' for d in ledger.values()),'semantic corrections:',len(out))
