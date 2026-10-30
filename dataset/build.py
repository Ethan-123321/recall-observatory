"""Rebuild a source-traceable dataset from saved official-page web text extracts.
No network calls. Does not infer exact batch/date rules for consumer verification.
"""
from pathlib import Path
import re, json, csv, sqlite3, hashlib, collections, runpy

ROOT=Path(__file__).resolve().parent
FIELDS={
 '生产者名称':'producer','产品名称':'product_name','品牌':'brand','型号/规格':'model_raw',
 '生产起止日期':'production_dates_raw','涉及数量':'quantity_raw','生产批号/批次':'batch_raw',
 '产品描述及外观照片':'description_raw','存在的缺陷':'defect_raw','可能导致的后果':'consequence_raw',
 '避免损害发生的应急处置方式':'emergency_raw','具体召回措施':'remedy_raw',
 '召回负责机构':'responsible_raw','召回联系方式':'contact_raw','召回进度安排':'schedule_raw',
 '其他需要报告的内容':'other_report_raw','其他信息':'other_info_raw'}
NULLS={'／', '\\', '','/','无','--','—','不详','未标注','未标识'}

def clean(s):
 s=re.sub(r'cite.*?','',s)
 return re.sub(r'\s+',' ',s).strip(' |　')

def category(name):
 name=re.sub(r'\s+','',name)
 for label,pattern in [
  ('玩具','玩具|磁力棒|彩泥|遥控车|过家家'),('婴童用品','婴儿|学步车|儿童衣柜'),
  ('服饰鞋包','服饰|卫衣|T恤|短袖|长袖|针织|凉鞋|运动鞋|书包|床笠'),
  ('文具','文具|笔|橡皮|圆规'),('食品接触用品','纸盒|纸碗|沙拉碗|纸杯'),
  ('照明电器','灯具|筒灯|吸顶灯|平板灯|染色灯'),('个护电器','光疗灯|美容仪|吹风机'),
  ('家用电器','吸尘|洗地|垃圾处理|排气|换气|灭蚊|绞肉|电烤|暖桌|电热|取暖'),
  ('电源电器','电源|充电器|插座'),('防护消防用品','头盔|灭火|口罩|软管'),
  ('家具家居','桌子|茶几|床垫|衣柜'),('饰品','戒指')]:
  if re.search(pattern,name):return label
 return '待分类'

def parse(doc,path):
 original_doc=doc
 m=re.search(r'\((https://www\.samrdprc\.org\.cn/(?:xfpzh/xfpzhgg/\d{6}|fzlm/zhgg/xfpzhgg/art/\d{4})/[^)]+\.html)\)',doc)
 if not m:return None
 url=m.group(1)
 title=re.search(r'^L\d+: # (.+)',doc,re.M)
 if not title and '/fzlm/' in url:title=re.search(r'^L2: (.+)',doc,re.M)
 if not title:return {'url':url,'error':'未取得正文标题','extract_file':path.name}
 doc=re.sub(r'(?<!\n)(L\d+:)',r'\n\1',doc)
 lines=[clean(x) for x in re.findall(r'^L\d+: (.*)',doc,re.M)]
 text='\n'.join(lines)
 date=re.search(r'发布时间[：:]\s*(\d{4}-\d{2}-\d{2})',text)
 # Handle table rows with | separators and vertically extracted table cells alike.
 tokens=[]
 for line in lines:
  tokens.extend(clean(v) for v in line.split('|') if clean(v))
 # A few vertically extracted headers wrap into two cells/lines.
 for first,second in [('产品描述及','外观照片'),('可能导致的','后果')]:
  i=0
  while i<len(tokens)-1:
   if tokens[i]==first and tokens[i+1]==second:tokens[i:i+2]=[first+second]
   i+=1
 values={};current=None
 for token in tokens:
  key=re.sub(r'\s','',token).replace('／','/')
  if key in ['产品描述及外观图片','产品外观特征及照片','产品描述及外观照片']:key='产品描述及外观照片'
  if key=='存在缺陷':key='存在的缺陷'
  if key=='应急处置方式':key='避免损害发生的应急处置方式'
  matched=next((k for k in FIELDS if key==k or (k=='涉及数量' and key.startswith(k+'（'))),None)
  if matched:current=FIELDS[matched];values.setdefault(current,[])
  elif token.startswith(('上一篇','下一篇','友情')):current=None
  elif current:values[current].append(token)
 fields={k:clean(' '.join(v)) for k,v in values.items()}
 for k in FIELDS.values():fields.setdefault(k,None)
 for k,v in list(fields.items()):
  if v in NULLS:fields[k]=None
 q=fields['quantity_raw'] or ''
 qcompact=re.sub(r'\s+','',q)
 qmatch=re.fullmatch(r'([\d,，]+)\s*(台|件|个|具|套|只|双|条|盒|张|支|盏|顶|床|包|把|批|米|辆|本|片)?',qcompact)
 count=int(re.sub('[,，]','',qmatch[1])) if qmatch else None
 name=fields['product_name'] or title[1]
 consequence=re.sub(r'\s+','',fields['consequence_raw'] or '')
 risk_rules={'触电':'触电|电击|漏电','火灾/燃烧':'火灾|起火|燃烧|复燃','窒息/误吞':'窒息|误吞|吞食|吞咽','割伤/刺伤':'割伤|划伤|刺伤|锐利|尖端','烫伤':'烫伤|灼伤','化学健康风险':'邻苯|甲醛|铅|镉|硼|化学|生殖|致癌|恶性疾病','机械伤害':'摔伤|夹伤|挤夹|碰伤|砸伤|撞伤|倾翻|倾倒|头部伤|头部受伤','听力损伤':'听力','爆炸':'爆炸'}
 risks=[k for k,v in risk_rules.items() if re.search(v,consequence)]
 flags=[]
 for k in ['producer','product_name','model_raw','production_dates_raw','defect_raw','consequence_raw','remedy_raw']:
  if not fields[k]:flags.append('missing:'+k)
 if count is None:flags.append('quantity_requires_review')
 if not risks:flags.append('risk_requires_review')
 if any(len(v)>500 for v in fields.values() if v):flags.append('long_field_review')
 return dict(id=url.rsplit('/',1)[-1][:-5],source_url=url,title=title[1],published_date=date[1] if date else None,
  retrieved_date='2026-10-20' if 'v5' in path.name else '2026-10-19' if 'v4' in path.name else '2026-10-16',source='国家市场监督管理总局缺陷产品召回技术中心',
  retrieval_method='web_tool_text_extract',extract_file='raw/'+path.name,
  extract_sha256=hashlib.sha256(original_doc.encode()).hexdigest(),**fields,
  quantity=count,quantity_unit=qmatch[2] if qmatch else None,
  category=category(name),category_method='keyword_rule_v1',risk_tags=risks,risk_method='consequence_keyword_rule_v1',
  review_status='机器整理待逐条复核',quality_flags=flags)

def build():
 records={};failures=[];duplicates=0;quarantine=[]
 for path in sorted((ROOT/'raw').glob('batch-*.txt')):
  for doc in path.read_text(encoding='utf-8').split('-'*80):
   row=parse(doc,path)
   if not row:
    if 'Failed to fetch' in doc:failures.append({'extract_file':path.name,'reason':clean(doc)[:450]})
    continue
   if 'error' in row:failures.append(row);continue
   if row['source_url'] in records:duplicates+=1
   records[row['source_url']]=row
 rows=sorted(records.values(),key=lambda r:(r['published_date'] or '',r['id']),reverse=True)
 quarantine=[r for r in rows if not r['product_name'] or not r['defect_raw']]
 rows=[r for r in rows if r not in quarantine]
 (ROOT/'quarantine.json').write_text(json.dumps(quarantine,ensure_ascii=False,indent=2),encoding='utf-8')
 overrides=json.loads((ROOT/'review-overrides.json').read_text(encoding='utf-8'))
 for r in rows:
  r['quantity_method']='single_value_parse'
  r['review_note']=None
  if r['id'] in overrides:
   r.update(overrides[r['id']]);r['quantity_method']='manual_field_review'
   r['quality_flags']=[f for f in r['quality_flags'] if f!='quantity_requires_review']
  if not r['quantity_unit']:r['quality_flags'].append('quantity_unit_missing')
 rows=runpy.run_path(str(ROOT/'review-v2.py'))['apply_review'](rows)
 with (ROOT/'review-ledger.csv').open('w',encoding='utf-8-sig',newline='') as f:
  keys=['id','product_name','category','risk_tags','batch_review_status','batch_review_note','scope_assessment','scope_assessment_reason','scope_details','source_url','reviewer','reviewed_at']
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
  for r in rows:w.writerow({k:json.dumps(r.get(k),ensure_ascii=False) if isinstance(r.get(k),(list,dict)) else r.get(k) for k in keys})
 (ROOT/'recalls.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
 (ROOT.parent/'dist'/'dataset.js').write_text('const recallDataset = '+json.dumps(rows,ensure_ascii=False,indent=2)+';\n',encoding='utf-8')
 if rows:
  with (ROOT/'recalls.csv').open('w',encoding='utf-8-sig',newline='') as f:
   w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader()
   for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in r.items()})
 db=sqlite3.connect(ROOT/'recalls.sqlite3')
 db.execute('CREATE TABLE IF NOT EXISTS recalls (id TEXT PRIMARY KEY, published_date TEXT, product_name TEXT, category TEXT, quantity INTEGER, source_url TEXT UNIQUE, record_json TEXT NOT NULL)')
 with db:
  db.execute('DELETE FROM recalls')
  db.executemany('INSERT INTO recalls VALUES (?,?,?,?,?,?,?)',[(r['id'],r['published_date'],r['product_name'],r['category'],r['quantity'],r['source_url'],json.dumps(r,ensure_ascii=False)) for r in rows])
 db.close()
 report={'retrieved_date':'2026-10-20','unique_announcements':len(rows),'quarantined':len(quarantine),'scope_assessment':dict(collections.Counter(r.get('scope_assessment') for r in rows)),'review_status':dict(collections.Counter(r['review_status'] for r in rows)),'batch_review_status':dict(collections.Counter(r.get('batch_review_status','未复核') for r in rows)),'duplicate_extracts':duplicates,'failed_extracts':failures,
 'published_date_range':[min((r['published_date'] for r in rows if r['published_date']),default=None),max((r['published_date'] for r in rows if r['published_date']),default=None)],
 'categories':dict(collections.Counter(r['category'] for r in rows)),
 'field_missing':{k:sum(r.get(k) is None for r in rows) for k in FIELDS.values()},
 'quality_flags':dict(collections.Counter(f for r in rows for f in r['quality_flags'])),
 'scope':'多个历史官方列表页及新版官方公告的可访问样本；网页检索缓存可能来自不同时间。非全量、非连续时间覆盖，不代表市场发生率。'}
 (ROOT/'quality-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':
 import sys
 sys.stdout.reconfigure(encoding='utf-8')
 build()
