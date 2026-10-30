"""Persist the scope decisions made while reading all 764 source field/range blocks.
Run deliberately after review, never as a classification step in the dataset builder.
"""
from pathlib import Path
from html.parser import HTMLParser
import json,re,hashlib
ROOT=Path(__file__).resolve().parent
load=lambda n:json.loads((ROOT/n).read_text(encoding='utf-8-sig'))
class Body(HTMLParser):
 def __init__(self):super().__init__();self.depth=0;self.skip=0;self.parts=[]
 def handle_starttag(self,t,attrs):
  if not self.depth and dict(attrs).get('id')=='zoom':self.depth=1;return
  if self.depth:
   if t=='div':self.depth+=1
   if t in ['script','style']:self.skip+=1
   if t in ['p','br','tr']:self.parts.append('\n')
 def handle_endtag(self,t):
  if self.depth and t=='div':self.depth-=1
  if t in ['script','style']:self.skip=max(0,self.skip-1)
 def handle_data(self,s):
  if self.depth and not self.skip:self.parts.append(s)
 def text(self):return '\n'.join(re.sub(r'\s+',' ',s).strip() for s in ''.join(self.parts).splitlines() if s.strip())
q=load('semantic-review-queue.json');out={}
special={
128:'生产日期2021年与批号20240409不一致，批号不改写为生产日期，需厂家确认。',
157:'批号20206010不是可确定日期，保留原字符，不纠正为20210610。',
158:'原文生产起止日期2021年11月3日至2011年11月4日倒置，不能猜填2011为2021，需厂家确认。',
197:'原批号20260712—20270925与生产期2023—2024年不同，不将批号自动解释为生产日期或有效期。',
215:'原文2022年9年11日日期格式有误，保留文字，不猜填。',
250:'TDT6021Z的部分批号含2020年，与2022年生产期不同，不能纠正批号或扩大日期，需厂家确认。',
352:'型号写见附件，但本地HTML无对应附件链接；仅有置物盘范围，具体型号待厂家提供。原文明确非食品接触产品，不能当餐具使用。',
385:'10个产品、规格与货号原文并列，只有两个生产月份，未明确逐一对应关系，不能强行按顺序跨字段配对。末尾货号连接处亦不明确。',
499:'原HTML型号单元格为图片；已本地OCR并视觉核对16个型号。批号为含通配符的编码，不展开为确定序列。',
596:'原日期注明进口报关日期，不能当作生产日期。',
659:'原文车架号详见附件，但HTML唯一图片是自行车外观图，未提供车架号名单。须厂家核实具体车架号。',
727:'批号2020-06-20早于2021年生产期，保留原文并要求厂家确认。',
488:'多生产者联合召回的正式备案公告，不是汇总新闻；未披露生产日期，按逐品牌数量原文保存，总数1756辆，不再加上各分组。',
489:'多生产者联合召回的正式备案公告；生产日期未披露，品牌分组原文保存，总数1993辆，不累加分组。',
595:'多生产者联合召回的正式备案公告；生产日期未披露，品牌分组原文保存，总数2174辆，不累加分组。',
599:'多生产者联合召回的正式备案公告；生产日期未披露，品牌分组原文保存，总数2312辆，不累加分组。',
31:'同一林肯飞行家范围2286辆对应不同缺陷组，不能按两组直接求独立车辆总数。',
50:'部分厢式运输车10辆在不同缺陷组重复出现，不按组累加独立车辆数。',
51:'青岛基地158辆在不同缺陷组重复出现，不能累加为316辆。',
76:'同一98辆在不同缺陷组重复，不按组累计独立车辆。',
79:'同一66辆在不同缺陷组重复，不按组累计独立车辆。',
107:'总数30931台包括车辆型号BJ7000MBEVR2及另一型号子组，不将总数与子数相加。',
531:'部分范围为售后更换燃油泵时间，不是生产日期；完整保留每组限定语，不能自动与其他生产期混合。',
567:'三组生产期限定其后全部品牌车型；分号后仅重复年款，不应遗漏前面的昂科威、君越、君威、探界者、迈锐宝、XT4等车型。',
757:'原文总数14辆，包含XC90 13辆及V90CC 1辆，不累加为28辆。'}
uncertain={128,157,158,197,215,250,352,385,659,727}
for i,r in enumerate(q):
 raw=(ROOT/r['raw_file']).read_bytes();assert hashlib.sha256(raw).hexdigest()==r['sha256']
 p=Body();p.feed(raw.decode('utf8'));body=p.text()
 car='/qc' in r['source_url'] or '汽车'==r.get('category')
 # The fixed queue contains the original domain, not a new keyword classification.
 car=r.get('domain')=='汽车' if 'domain' in r else car
 if car:
  paragraphs=[s for s in body.splitlines() if ('生产' in s and re.search(r'\d{4}年',s) and re.search(r'\d[辆台件套个]',s)) or '分别召回' in s or ('召回编号' in s and re.search(r'共计.*[辆台件]',s))]
  assert paragraphs,(i,r['id'])
  evidence='\n'.join(paragraphs)
  fields=dict(model_raw='车型/配件与范围逐组见原文（不展开交叉组合）',production_dates_raw=evidence,batch_raw=None,quantity_raw=None,quantity=None,quantity_unit=None)
  # Only normalize a single explicit total when no other numeric unit clause exists.
  quantities=re.findall(r'(?:共计|共)([\d,，]+)(辆|台|件|套|个)',evidence)
  allcounts=re.findall(r'([\d,，]+)(辆|台|件|套|个)',evidence)
  if len(quantities)==1 and len(allcounts)==1:
   n,u=quantities[0];fields.update(quantity_raw=n+u,quantity=int(n.replace(',','').replace('，','')),quantity_unit=u)
  elif quantities:fields['quantity_raw']='；'.join(n+u for n,u in quantities)
  if i in [488,489,595,599]:fields.update(quantity=[1756,1993,2174,2312][[488,489,595,599].index(i)],quantity_unit='辆',quantity_raw='原文明确总计：'+[ '1756','1993','2174','2312'][[488,489,595,599].index(i)]+'辆（各品牌见范围原文）')
  groups=[dict(model='原文第'+str(j+1)+'组（可含子组）',source_dates=s,evidence=s) for j,s in enumerate(paragraphs)]
 else:
  sf=r['source_fields'];fields={k:sf.get(k) for k in ['model_raw','production_dates_raw','batch_raw','quantity_raw']}
  evidence='\n'.join(k+'：'+str(v) for k,v in fields.items() if v is not None)
  groups=[dict(model=fields['model_raw'],source_dates=fields['production_dates_raw'],batch_raw=fields['batch_raw'],quantity_raw=fields['quantity_raw'])]
  if i==499:
   fields['model_raw']='A045R002L；A065R009L；A065R009L -T002；ADP-65JH BBA；ADP-90CD BBA；ADS-75SB BBDA；HP-A0301 R3 B5LF；PA-1121-04TJ；PA-1300-04TP；PA-1450-82 TP；PA-1650-22TJ；PA-1650-82 TP；PA-1750-29TJ；PA-1750-82TP；PA-1900-36TJ；PA-1900-82 TP'
   groups[0]['model']=fields['model_raw']
 note=special.get(i,'保留原文组号、产品型号、生产日期及批号的限定关系；不展开离散日期，不累加多组数量。')
 if not car and (not fields.get('batch_raw') or re.fullmatch(r'[/—\-\s无]+|[一\d]+批次?',fields.get('batch_raw') or '')):note+='批次空白、无、斜杠或只有批次数量，均不是全部批次召回。'
 if car:note+='汽车及配件须按VIN/零件号向厂家确认；原文未单列批次，保留缺失。'
 out[r['id']]=dict(source_sha256=r['sha256'],queue_index=i,fields=fields,evidence=evidence,
  review_dimensions=['model_raw','production_dates_raw','batch_raw','quantity_raw'],
  status='范围条件部分复核·需厂家确认' if i in uncertain else '范围条件AI辅助复核',note=note,
  method='Codex逐条阅读公告范围字段/生产范围段落；不表示生产者、全部措施或全文转录已复核',reviewed_at='2026-10-23',
  scope_details=dict(status='原文关联整体保存；同组多个日期/车型不自动生成交叉组合',groups=groups))
 if i==499:out[r['id']]['images']=[x for x in load('scope-image-ledger.json') if x['queue_index']==499]
(ROOT/'scope-decisions-2023-2025.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
print('Persisted scope decisions:',len(out),'cars:',sum('汽车及配件' in d['note'] for d in out.values()))
