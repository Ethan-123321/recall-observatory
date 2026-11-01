"""Reproducible source-backed normalization. Rule labels are NOT human review."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit
import importlib.util,json,re,hashlib,csv,sqlite3,collections,sys,subprocess
import review_pipeline
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('old',ROOT/'collect-2025.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
def load(name):return json.loads((ROOT/name).read_text(encoding='utf-8-sig'))
def dump(name,obj):(ROOT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
class Body(HTMLParser):
 def __init__(self):super().__init__();self.depth=0;self.skip=0;self.parts=[]
 def handle_starttag(self,t,attrs):
  a=dict(attrs)
  if not self.depth and a.get('id')=='zoom':self.depth=1;return
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
CATEGORY=[('食品接触用品','杯|碗|餐具|餐盒|水壶|水瓶|奶瓶|保鲜|饭盒|筷|勺|吸管|铝锅|铁锅|不粘锅'),('玩具','玩具|积木|毛绒|弹射|磁力珠'),('婴童用品','童车|婴儿|婴幼儿|儿童推车|儿童座椅'),('电源电器','电源|充电|插座|插头|电池|转换器|插排'),('照明电器','灯|照明'),('个护电器','吹风|卷发|烫发|剃须|理发|直发'),('燃气器具','燃气|煤气|调压器'),('防护消防用品','头盔|口罩|灭火|消防|呼吸器|安全帽'),('服饰鞋包','服装|裤|衫|裙|鞋|袜|背包|书包|帽子|外套|皮带|手套|围巾'),('文具','笔|文具|本子|作业本|课文本|拼音本|画棒|橡皮|涂改|修正|卷笔|尺子'),('家具家居','椅|桌|柜|床|家具|沙发|凳|晾衣'),('电动自行车','电动自行车|电动滑板'),('自行车及配件','自行车|轮组'),('运动用品','球|滑板|轮滑|健身|跳绳|护具'),('光学用品','眼镜|镜片'),('数码通信产品','耳机|音箱|鼠标|键盘|路由|手机|平板'),('家用电器','电|器|风扇|加湿|烤箱|冰箱|洗衣|空调|炉|灶'),('饰品','首饰|项链|耳饰|戒指|手链'),('日用清洁护理','清洁|洗涤|洗衣液|指甲|牙刷')]
RISK=[('触电','触电'),('火灾/燃烧','火灾|起火|燃烧|自燃'),('窒息/误吞','窒息|误吞|吞咽|吞食'),('割伤/刺伤','割伤|划伤|刺伤|锐利|锐边|锐尖'),('烫伤','烫伤|灼伤'),('化学健康风险','甲醛|重金属|铅含量|镉|邻苯|化学|迁移|防腐剂|添加剂|农药|兽药|铝残留|二氧化硫'),('机械伤害','夹伤|挤伤|跌落|摔伤|机械伤害|缠绕'),('爆炸','爆炸'),('防护失效','防护失效|不能.*防护|灭火性能'),('听力损伤','听力'),('视力影响','视力|眼睛'),('微生物污染','菌落|菌总数|大肠|霉菌|微生物|沙门|李斯特菌'),('碰撞/失控风险','碰撞|失控|转向失效|制动失效|失去.*动力|失去.*制动|增加.*事故|发生事故'),('人员伤害','人身伤害|人员受伤|乘员.*伤害|伤及')]
reviewed={r['id']:r for r in load('recalls-2025-reviewed.json')}
rows=[];excluded=[]
for channel,domain in [('consumer','一般消费品'),('cars','汽车')]:
 for src in load(channel+'-collected.json'):
  r=dict(src);r['id']=Path(urlsplit(r['source_url']).path).stem
  if r['id'] in reviewed:r={**reviewed[r['id']],**{'domain':domain,'year':r['published_date'][:4],'source_coverage':'召回中心消费品栏目'}};rows.append(r);continue
  raw=(ROOT/r['raw_file']).read_bytes();p=old.Page();p.feed(raw.decode('utf-8'));b=Body();b.feed(raw.decode('utf-8'));body=b.text()
  if p.meta.get('ArticleTitle')!=r['title'] or len(body)<100:excluded.append({**r,'exclude_reason':'正文缺失、图片正文或标题不匹配，未纳入自动分类'});continue
  fields={}
  for i,cell in enumerate(p.cells[:-1]):
   key=re.sub(r'\s+','',cell).replace('／','/');field=old.FIELD_NAMES.get(key)
   if key.startswith('涉及数量'):field='quantity_raw'
   if field:fields[field]=p.cells[i+1]
  if domain=='汽车':
   paras=body.splitlines();ranges=[s for s in paras if re.search(r'生产.*(?:辆|件|汽车)|召回编号',s)]
   defect=[s for s in paras if re.search('本次召回范围内|本次召回的|本次召回车辆|由于.*可能',s)]
   fields=dict(producer=r['title'].split('召回')[0],product_name=r['title'].split('召回',1)[-1],model_raw=None,production_dates_raw='\n'.join(ranges) or None,batch_raw=None,quantity_raw=None,defect_raw='\n'.join(defect) or None,consequence_raw=None,remedy_raw='\n'.join(s for s in paras if '免费' in s) or None)
  if not fields.get('defect_raw'):
   excluded.append({**r,'exclude_reason':'缺陷正文尚未结构化，暂不计入分析'});continue
  r.update(fields);r.update(domain=domain,year=r['published_date'][:4],source_text=body,source_fields=fields.copy(),source_coverage='召回中心'+('汽车' if domain=='汽车' else '消费品')+'栏目')
  for k in old.FIELD_NAMES.values():r.setdefault(k,None)
  r['product_name']=r.get('product_name') or r['title']
  if re.fullmatch(r'[A-Z0-9]{18}',r['product_name']):r['product_name']=r['title'].split('召回',1)[-1]
  r['category']='汽车' if domain=='汽车' else next((c for c,pat in CATEGORY if re.search(pat,r['product_name'])),'其他消费品')
  if r['category']=='其他消费品':
   if re.search('玩具|遥控车|陀螺|软弹枪|过家家',r['product_name']+' '+(r.get('defect_raw') or '')):r['category']='玩具'
   elif re.search('洗洁|洗衣|洗涤',r['product_name']):r['category']='日用清洁护理'
   elif re.search('书橱|书架',r['product_name']):r['category']='家具家居'
   elif re.search('串珠|手串',r['product_name']):r['category']='饰品'
  text=(r.get('defect_raw') or '')+' '+(r.get('consequence_raw') or '')
  r['risk_evidence']={tag:[m.group() for m in re.finditer(pat,text)] for tag,pat in RISK if re.search(pat,text)}
  r['risk_tags']=list(r['risk_evidence']) or ['未明确具体伤害']
  r['category_method']='产品名称关键词规则 v1（可追溯，非逐条人工复核）';r['risk_method']='仅对缺陷及后果字段匹配风险词 v1；命中词留存，标签为辅助编码'
  r['review_status']='已结构化·规则标注';r['extraction_status']='正文与来源字段已提取';r['automated_match_enabled']=False;r['analysis_eligible']=True
  r['scope_assessment']='范围细节需补充确认';r['batch_review_note']='已保留型号、日期和批次原文；未自动建立跨型号对应关系。批次缺失不代表全部批次。'+('汽车必须进一步按VIN向厂家核实。' if domain=='汽车' else '')
  r['quality_flags']=['分类与风险为规则辅助编码，未标记为逐条语义复核。'];r['quantity']=None;r['quantity_unit']=None
  q=re.fullmatch(r'\s*([\d,，]+)\s*(个|件|台|只|套|辆|双|包|袋|本)\s*',r.get('quantity_raw') or '')
  if q:r['quantity']=int(q[1].replace(',','').replace('，',''));r['quantity_unit']=q[2]
  if domain=='汽车':
   # Keep complete range clauses instead of inventing a normalized model list.
   r['model_raw']='车型与生产范围见下方公告原文'
   amounts=re.findall(r'(?:共计|共)([\d,，]+)(辆|件|套|个)',body)
   if len(amounts)==1:r['quantity']=int(amounts[0][0].replace(',','').replace('，',''));r['quantity_unit']=amounts[0][1];r['quantity_raw']=''.join(amounts[0])
   elif amounts:r['quantity_raw']='；'.join(''.join(x) for x in amounts)
   r['quality_flags'].append('车型与生产区间保留完整原文；多组数量不自动相加，未单独建立VIN清单。')
  r['source_missing_fields']=[k for k in ['model_raw','batch_raw'] if not r.get(k)]
  rows.append(r)
# Food is a documented regional sample, not nationwide or full-period coverage.
food=ROOT/'food-fujian-collected.json'
if food.exists():
 transcriptions=load('food-transcriptions.json')
 for src in load(food.name):
  transcription=transcriptions.get(src.get('id'))
  if transcription:src={**src,'source_text':'\n'.join(str(v) for v in transcription.values() if v),'transcription_method':'AI视觉核对PDF第一页关键字段；非全文转录'}
  body=re.sub(r'\s+','',src.get('source_text',''))
  if len(body)<100 or '召回' not in body:excluded.append({**src,'exclude_reason':'食品PDF未提取到足够文本，待图像转录'});continue
  r=dict(src);r.update(domain='食品',year=r['published_date'][:4],category='食品',product_name=r['title'],producer=r['title'].split('食品召回')[0],brand=None,model_raw=None,production_dates_raw=None,batch_raw=None,quantity_raw=None,quantity=None,quantity_unit=None,defect_raw=body,consequence_raw=None,remedy_raw=None,source_coverage='福建省食品召回栏目有限样本',scope_assessment='范围细节需补充确认',batch_review_note='食品按生产日期、批号及规格核对；正文完整保留，未自动判断具体产品命中。',review_status='已提取·规则标注',extraction_status='PDF文本已提取',automated_match_enabled=False,analysis_eligible=True,quality_flags=['区域样本，不代表全国食品召回；字段与风险由规则辅助整理。'],source_missing_fields=['model_raw','batch_raw'],category_method='食品召回专栏及公告标题',risk_method='PDF原文关键词匹配；非人工专家复核')
  r['risk_evidence']={tag:[m.group() for m in re.finditer(pat,body)] for tag,pat in RISK if re.search(pat,body)};r['risk_tags']=list(r['risk_evidence']) or ['未明确具体伤害']
  if transcription:
   r.update(transcription);r['review_status']='已完成AI辅助图像字段复核';r['extraction_status']='PDF关键字段视觉转录';r['risk_method']='按PDF缺陷字段逐条编码';r['source_missing_fields']=[k for k in ['model_raw','batch_raw'] if not r.get(k)];r['quality_flags']=['福建区域有限样本；原公告未写的字段保留为空。'];r['source_fields']=transcription.copy()
  rows.append(r)
rows,excluded=review_pipeline.apply(rows,excluded)
# Food evidence is retained in the archive but excluded from the published scope.
rows=[r for r in rows if r.get("domain") != "食品"]
excluded=[r for r in excluded if r.get("domain") != "食品"]
contact_spec=importlib.util.spec_from_file_location('contact_evidence',ROOT/'complete-contact-evidence.py')
contact_module=importlib.util.module_from_spec(contact_spec);contact_spec.loader.exec_module(contact_module)
rows=contact_module.apply(rows)
rows=json.loads(subprocess.run(['node',str(ROOT/'enrich-scopes.cjs')],input=json.dumps(rows,ensure_ascii=False),text=True,encoding='utf-8',capture_output=True,check=True).stdout)
subprocess.run([sys.executable,'-X','utf8',str(ROOT/'inventory-scope-sources.py'),'--stdin'],input=json.dumps(rows,ensure_ascii=False),text=True,encoding='utf-8',capture_output=True,check=True)
rows=json.loads(subprocess.run(['node',str(ROOT/'resolve-source-scopes.cjs')],input=json.dumps(rows,ensure_ascii=False),text=True,encoding='utf-8',capture_output=True,check=True).stdout)
rows=json.loads(subprocess.run(['node',str(ROOT/'resolve-reviewed-scopes.cjs')],input=json.dumps(rows,ensure_ascii=False),text=True,encoding='utf-8',capture_output=True,check=True).stdout)
unique=[];seen={};duplicates=[]
for r in rows:
 signature=tuple(re.sub(r'\s+','',r.get(k) or '') for k in ['published_date','title','model_raw','defect_raw'])
 if signature in seen:duplicates.append({'id':r['id'],'duplicate_of':seen[signature]['id']});continue
 seen[signature]=r;unique.append(r)
unique.sort(key=lambda r:(r['published_date'],r['id']),reverse=True)
unique=json.loads(subprocess.run(['node',str(ROOT/'build-scope-backlog.cjs')],input=json.dumps(unique,ensure_ascii=False),text=True,encoding='utf-8',capture_output=True,check=True).stdout)
report=dict(generated_date='2026-10-25',count=len(unique),by_domain=dict(collections.Counter(r['domain'] for r in unique)),by_year=dict(collections.Counter(r['year'] for r in unique)),by_status=dict(collections.Counter(r['review_status'] for r in unique)),excluded_count=len(excluded),duplicates=duplicates,coverage=['一般消费品与汽车：官方栏目2023—2025目录遍历，正文无法可靠解析的公告另列排除清单','统计单位为去重公告，不是全国召回事件；不同领域的数量不能用于安全排名'])
report.update(review_pipeline.quality(unique))
report['generated_date']='2026-11-01'
dump('recalls-2023-2025.json',unique);dump('quality-multidomain.json',report);dump('excluded-multidomain.json',excluded)
(ROOT.parent/'dist'/'dataset-multidomain.js').write_text('const recallDataset = '+json.dumps(unique,ensure_ascii=False)+';\nconst recallCoverage = '+json.dumps(report,ensure_ascii=False)+';\n',encoding='utf-8')
with (ROOT/'recalls-2023-2025.csv').open('w',encoding='utf-8-sig',newline='') as f:
 keys=['id','domain','year','published_date','title','category','risk_tags',*review_pipeline.FIELDS,'review_status','review_stages','source_url','sha256','record_json'];w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
 for r in unique:w.writerow({k:json.dumps(r if k=='record_json' else r.get(k),ensure_ascii=False) if k=='record_json' or isinstance(r.get(k),(list,dict)) else r.get(k) for k in keys})
with sqlite3.connect(ROOT/'recalls-2023-2025.sqlite3') as db:
 db.execute('CREATE TABLE IF NOT EXISTS notices(id TEXT PRIMARY KEY,domain TEXT,year TEXT,published_date TEXT,category TEXT,record_json TEXT)');db.execute('DELETE FROM notices');db.executemany('INSERT INTO notices VALUES(?,?,?,?,?,?)',[(r['id'],r['domain'],r['year'],r['published_date'],r['category'],json.dumps(r,ensure_ascii=False)) for r in unique])
subprocess.run(['node', str(ROOT/'build-quality.cjs')], check=True)
subprocess.run([sys.executable,str(ROOT.parent/'research'/'build_tasks.py')],check=True)
sys.stdout.reconfigure(encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2))
