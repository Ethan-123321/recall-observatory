"""Reproducible 2025 source review. Explicit AI-assisted decisions, not expert certification.
Keeps the collection snapshot unchanged; produces reviewed catalogue and deduplicated analysis.
"""
from pathlib import Path
import json,re,csv,sqlite3,hashlib,collections,sys
ROOT=Path(__file__).resolve().parent
DATE='2026-10-22'
CATS= {'H':'家用电器','P':'个护电器','S':'防护消防用品','W':'文具','C':'服饰鞋包','F':'家具家居','T':'玩具','K':'食品接触用品','L':'照明电器','B':'婴童用品','E':'电源电器','J':'饰品','O':'光学用品','V':'电动自行车','D':'无人机','G':'日用清洁护理','Y':'运动用品','R':'燃气器具','Z':'自行车及配件','I':'数码通信产品','U':'乐器配件','Q':'日用杂品'}
RISKS={'e':'触电','f':'火灾/燃烧','s':'窒息/误吞','c':'割伤/刺伤','b':'烫伤','h':'化学健康风险','m':'机械伤害','a':'听力损伤','x':'爆炸','p':'防护失效','u':'未明确具体伤害','v':'视力影响','z':'空域及公共安全','i':'皮肤刺激/过敏','g':'微生物污染','t':'一氧化碳中毒','q':'呼吸不适','w':'水源污染'}
NULLS={'','/','／','无','--','—','－','-','--/--','—/—','未设生产批号'}
def dump(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def compact(s):return re.sub(r'\s+','',s or '')
assert hashlib.sha256((ROOT/'annual-2025.json').read_bytes()).hexdigest()=='1d9d8d56905c3386aead91a86ff6dd19e2c72777ce85dc7c4f50f763b3236e3f', 'Collection snapshot changed: review decisions must be remapped by ID before rebuild'
annual=json.loads((ROOT/'annual-2025.json').read_text(encoding='utf-8'))
rows=annual['records']
decisions={int(a):(b,c) for a,b,c in (l.split() for l in (ROOT/'annual-review-decisions.txt').read_text().splitlines())}
assert set(decisions)==set(range(342))
# Visually transcribed from preserved official JPGs, not inferred from titles.
images={5:dict(producer='海南丰瑞康科技有限公司',product_name='V850碗',brand='丰瑞康',model_raw='25个/袋',production_dates_raw='2025-07-10 — 2025-07-10',quantity_raw='360袋',batch_raw='2025-07-10',defect_raw='渗漏性能（油的渗漏性能）项目不符合Q/FRK1-2024《全生物降解餐用纸制品》标准要求',consequence_raw='可能引发产品在使用中突然破裂，导致碗里面的热食或热饮渗漏，造成消费者烫伤等意外事故',emergency_raw='立即封存该批次生产的产品继续出库，立即告知各批发商此情况，停止出售',remedy_raw='立即联系各批发商对该批产的产品召回',schedule_raw='2026年1月10日—2026年2月28日'),324:dict(producer='广东岩羊照明有限公司',product_name='嵌入式LED灯具',brand='卡迪之光',model_raw='YY-TD-COB10A',production_dates_raw='2023年3月13日至2023年3月14日',quantity_raw='240只',batch_raw='YY23-III-13',defect_raw='外部接线和内部接线项目不符合GB 7000.1-2015和GB 7000.202-2008标准',consequence_raw='可能引起火灾、触电危险',emergency_raw='消费者立即暂停使用有缺陷的产品，联系公司或者经销商进行处理',remedy_raw='通知销售商立即停止销售缺陷产品，并在公司及销售商实体店铺发布召回公告，告知消费者具体召回事宜，为购买到缺陷产品的消费者免费退货处理',schedule_raw='2025年1月15日至2025年4月14日（具体以实际进度安排为准）')}
# Source anomalies stay visible rather than silently repaired.
NOTES={5:'目录发布日期为2025-12-30，图片计划写2026年召回进度；按公告发布日期归入2025，不把进度日期当发布日期。',14:'批号202307与2024年生产日期分别保留，不能把批号当生产日期。',21:'原文型号为斜杠；型号未披露，不编造。',24:'批次含区间及占位符，范围内是否受影响仍需厂家确认。',33:'原文只有9批次的数量，没有9个批号。',51:'原文型号为斜杠；规格可参考外观描述，但不填造型号。',62:'批次---/12/6不能确认为完整编码。',65:'批号20240320与所列生产日期不同，不能擅改。',69:'生产日期2023.3至今为开放区间，“今”不能替换成采集日。',83:'生产日期自2019年11月开始，批次却含201910-021；存在冲突，需厂家确认。',86:'两种头盔原型号重复，批次栏写2批次却只列一个日期；不可编造第二组。',108:'原文产品名称误填生产者；展示名称按公告标题整理为背包，原值单独保留。',129:'三个款号、三个生产区间和三个合同批号未明确逐项对应，保留三组文本，不按顺序猜配。',134:'生产日期为2011年，晚于该日期的标准被引用；原样保留，不改年份。',141:'型号与批次均未披露，以产品描述识别并向厂家核实。',143:'批次仅写通过SN查询；不能把该日期范围内全部产品视为召回。',152:'型号未披露，20190601批号与生产日分别保留。',157:'批号20200703与所列生产日不同，保留原值。',169:'生产日2024-01-15与批号20240117分别保留。',172:'日期原文“2021年2月—2021年4月30日1日”异常，不自动修正。',173:'批次含20212.11.3疑似笔误，不能自动改为2021.11.3。',181:'批号202008与生产区间不同，不能据此改写生产日。',202:'两个型号及2批次只列一个日期编码，对应关系需厂家确认。',213:'产品名称栏误填统一社会信用代码；按标题展示音乐玩具，保留原始字段。',215:'型号栏只列666-21，但缺陷及后果另提NO.666-10A；第二型号日期未明，不能跨型号套用。',237:'多产品、多规格、两个批次日期未逐项关联，需分别核实。',243:'生产区间起于2024-11-05，批次含2024-10-11，不能自动肯定命中。',244:'生产区间起于2023-12-03，批次写2023-12-1，需厂家确认。',264:'型号为占位符，未披露型号。',269:'型号栏写请详附件，已保存HTML未提供可下载的型号附件；不能补造型号，轮组需按厂家清单核实。',271:'批号21210110原样保留，不能按日期格式纠正。',290:'原文型号和批次栏为空。',291:'全部批次仅限所列BLL360型号及生产日期，不是全品牌。',292:'原文未列具体型号；其中3款指甲贴的风险并非所有款式都相同。',295:'型号未披露，保留镜片品牌及外观说明，不编造型号。',319:'四个型号分别对应四个生产日；4批次只是数量而非批号。',320:'数量末尾总计188件，分项单位为个；汇总沿用总计单位并保留原文。',327:'与另一网址的同日同标题公告核心字段完全一致，分析仅计一次；两条目录都保留。',329:'与目录索引327内容重复，分析排除本条，保留来源关联。',332:'四型号、两个日期区间、两个批次未明确逐项对应；不能按顺序猜配。'}
# Explicit multi-model associations only where the original names each group.
GROUPS={55:[('MFZ/ABC4','2024年4月21日','2024-04'),('MFZ/ABC5','2024年5月9日','2024-05')],74:[('LW-XD-25','2021年5月25日-26日','2021-05'),('LW-GLY030T','2021年12月12日-13日','2021-12'),('LW-GB250','2021年12月12日-13日','2021-12')],75:[('KA-I75','2022年2月10日','2022-02'),('KA-903-30','2022年5月15日','2022-05')],108:[('45*30*20cm','2025年8月3日','原文规格后括注日期'),('48*30*21cm','2025年8月6日','原文规格后括注日期')],173:[('MK11C05L','2021年5月1日-2022年2月28日','2021.7.12、20212.11.3（原文）'),('MC05L','2021年5月1日-2022年2月28日','2021.8.17、2021.12.1')],174:[('DNDG-2503-COB25W','2021年4月5日-9日','DN20210405'),('DN-CHLED-TD-0504-1','2021年3月15日-18日','DN20210315'),('LEDT5A','2021年4月6日-8日','DN20210406')],203:[('IDOC230-15 15W','2021年5月29日-30日','2021年5月'),('IDOC350-28 28W','2021年6月1日-2日','2021年6月')],234:[('Z0207D','2025年5月16日','未披露'),('Z0207A','2025年5月17日','未披露'),('Z0207B','2025年5月19日','未披露'),('Z0207F','2025年5月19日','未披露'),('Z0207C','2025年5月19日','未披露')],272:[('24K田字薄','原文总区间2024-06-05至2025-03-03','2024/6/5'),('25K拼写本','同公告总区间，具体批次见右','2024/12/27'),('36K数学英语作业本','同公告总区间','2025/2/28'),('16K课文本','同公告总区间','2025/3/2'),('B5数学双格作业本','同公告总区间','2025/3/3')],319:[('HS-M3060-32A','2019年6月5日','仅列4批次数量'),('HS-LSMD-9','2021年2月13日','仅列4批次数量'),('HS-M3030-20A','2021年6月27日','仅列4批次数量'),('HS-L114-12T','2021年6月26日','仅列4批次数量')],320:[('QF38+38W','2021年8月1日-2022年5月1日','LED-A210725-01'),('QF25-30W','2021年7月1日-2022年5月1日','LED-A210605-04'),('QF-36W','2021年8月1日-2022年5月1日','LED-A210721-02'),('QF-7W','2021年9月1日-2022年5月1日','LED-A210810-03')],322:[('RJB-TY-C-10X1500','2024年2月、2024年4月','2024年2月3日、2024年4月13日'),('RJB-TY-C-10X2000','2023年7月23日','2023年7月23日')],325:[('FV-15008','2020年9月1日','20200901012'),('FV-15010','2021年5月7日','20210507023')]}
UNRESOLVED={12,21,24,33,51,60,62,69,83,86,129,135,139,141,143,152,172,173,181,199,202,206,215,216,237,243,244,264,269,277,290,292,295,316,332}
DISCRETE={1,37,49,54,113,116,133,137,162,170,232,265}
TOTALS={23:(65300,'包'),55:(150,'个'),69:(617,'台'),74:(260,'只'),75:(11,'个'),86:(60,None),108:(2000,'个'),116:(89400,'包'),129:(61,'双'),173:(1300,'个'),174:(1225,'只'),202:(150,'只'),203:(20,'个'),234:(75000,'本'),237:(8940,'包'),319:(175,None),320:(188,'件'),325:(350,'个'),332:(180,'个')}
ledger=[]
for i,r in enumerate(rows):
    original={k:v for k,v in r.items() if k.endswith('_raw') or k in ['producer','product_name','brand']}
    r['source_fields']=original
    if i in images:
        r.update(images[i]);img=ROOT/'raw'/'annual-2025'/f'notice-{i:03}.jpg'
        r['image_evidence']={'file':str(img.relative_to(ROOT)),'sha256':hashlib.sha256(img.read_bytes()).hexdigest(),'method':'AI视觉逐字段转录并核对'}
        r['source_fields'].update(images[i])
    if i in [108,213]:r['product_name']={108:'背包',213:'音乐玩具'}[i]
    for k in ['brand','model_raw','batch_raw']:
        if compact(r.get(k)) in NULLS:r[k]=None
    c,risk=decisions[i];r['category']=CATS[c];r['risk_tags']=[RISKS[t] for t in risk]
    r['review_status']='已完成AI辅助文本复核';r['reviewed_at']=DATE;r['scope_reviewed_at']=DATE
    r['reviewer']='AI逐条核对原文；非人工专家认证';r['automated_match_enabled']=False
    r['analysis_eligible']=True;r['duplicate_of']=None
    r['source_missing_fields']=[k for k in ['model_raw','batch_raw'] if not r.get(k)]
    r['missing_fields']=[];r['extraction_status']='字段已核对（原文缺失已注明）' if r['source_missing_fields'] else '字段已核对'
    r['quality_flags']=[NOTES[i]] if i in NOTES else []
    if not r.get('model_raw') and i not in NOTES:r['quality_flags'].append('原公告未披露型号，不补造。')
    batch=compact(r.get('batch_raw'))
    if i in UNRESOLVED:
        assessment='范围细节需补充确认';reason='原文存在型号缺失、批次不完整、对应关系或日期冲突，不能据此自动确认产品命中。'
    elif i in GROUPS:
        assessment='多型号分别界定';reason='原文逐组列明型号及日期或批次，必须在同组内核对，禁止跨型号拼接。'
    elif i in DISCRETE:
        assessment='离散日期或批次分别界定';reason='按原文列出的日期或批次集合核对，不以首尾值生成连续区间。'
    elif '全部' in batch:
        assessment='明确限定范围内全部批次';reason='全部批次仍受公告产品、型号、规格及生产日期限制，不是品牌所有产品。'
    elif not batch or re.fullmatch(r'[一二三四五六七八九十0-9]+(?:个)?批次?',batch):
        assessment='按型号与生产日期界定';reason='公告未列额外可识别批号，按产品型号和生产日期初筛；批次数量不是批次编码。'
    else:
        assessment='需同时核对批次';reason='保留原文批次标识或区间，与型号及生产日期共同核对；形似日期的批号不替代生产日期。'
    r['scope_assessment']=assessment;r['scope_assessment_reason']=reason
    r['batch_review_note']=NOTES.get(i,reason)
    r['scope_details']={'status':r['batch_review_note'],'groups':[{'model':m,'dates':[],'source_dates':d,'batches':[b]} for m,d,b in GROUPS.get(i,[])]} if i in GROUPS or i in UNRESOLVED else None
    if i==16:r['batch_review_note']='两款裙子的缺陷不同：燕舞欢欣为绳带，蝶舞韶华为pH值；风险统计在公告层面多标签，不能把每个风险套到两款产品。'
    q=compact(r.get('quantity_raw'));m=re.match(r'^(\d[\d,，]*(?:\.\d+)?)(万)?(台|件|个|具|套|只|双|条|盒|张|支|盏|顶|床|包|把|批|米|辆|本|片|袋|副|付|瓶|对|桶)?(?=$|[（(])',q)
    r['quantity']=int(float(m[1].replace(',','').replace('，',''))*(10000 if m[2] else 1)) if m else None
    r['quantity_unit']=m[3] if m else None
    if i in TOTALS:r['quantity'],r['quantity_unit']=TOTALS[i]
    if r['quantity'] is None:r['quality_flags'].append('数量未归一化；统计排除该数量，公告计数仍保留。')
    if not r['quantity_unit']:r['quality_flags'].append('原文未明确数量单位，不猜测单位或参与单位总量汇总。')
    r['review_evidence']={k:r.get(k) for k in ['product_name','model_raw','production_dates_raw','batch_raw','defect_raw','consequence_raw']}
    r['category_method']='逐条依据产品名称、标题与用途复核'
    r['risk_method']='逐条依据缺陷及可能后果多标签复核；不代表已发生事故'
    ledger.append({'id':r['id'],'catalogue_index':i,'source_url':r['source_url'],'sha256':r['sha256'],'category':r['category'],'risk_tags':r['risk_tags'],'scope_assessment':assessment,'reviewed_at':DATE,'evidence':r['review_evidence'],'notes':r['quality_flags']})
# Exact core-field duplicates, preserving all catalogue URLs and dates.
seen={};unique=[]
keys=['published_date','title','producer','product_name','model_raw','production_dates_raw','batch_raw','quantity_raw','defect_raw','consequence_raw','remedy_raw']
for r in rows:
    signature=tuple(compact(r.get(k)) for k in keys)
    if signature in seen:
        r['duplicate_of']=seen[signature]['id'];r['analysis_eligible']=False
        seen[signature].setdefault('duplicate_sources',[]).append(r['source_url'])
    else:seen[signature]=r;unique.append(r)
annual.update(reviewed_date=DATE,reviewed_count=len(rows),analysis_count=len(unique),duplicate_count=len(rows)-len(unique),review_method='AI逐条文本复核；原文缺失与歧义保留；不自动判断实际产品命中')
annual['limitations']=['完整指该栏目2025年目录，不代表全国全部召回事件','342条目录，合并1条核心字段完全相同的重复公告后为341份分析记录；扩大召回及同产品不同公告未合并为事件','全部完成AI辅助文本复核，原文缺失、附件缺失与歧义保留，非人工专家认证','按目录及正文发布日期统计，PubDate迁移日期不参与年度筛选']
for m in annual['months']:
    subset=[r for r in rows if r['published_date'].startswith(m['month'])]
    m['structured']=len(subset);m['reviewed']=len(subset);m['analysis_count']=sum(r['analysis_eligible'] for r in subset)
report={'reviewed_at':DATE,'catalogue_count':len(rows),'reviewed_count':len(rows),'analysis_count':len(unique),'duplicate_count':len(rows)-len(unique),'source_model_missing':sum(not r.get('model_raw') for r in rows),'manufacturer_confirmation':sum(r['scope_assessment']=='范围细节需补充确认' for r in unique),'image_transcriptions':list(images),'category_counts':dict(collections.Counter(r['category'] for r in unique)),'risk_counts':dict(collections.Counter(t for r in unique for t in r['risk_tags'])),'duplicates':[{'id':r['id'],'duplicate_of':r['duplicate_of']} for r in rows if r['duplicate_of']],'limitations':['官方栏目公告口径，不等于全国召回事件全量','原文信息缺失不等于未复核；不编造缺失型号、批次或附件','不自动认定用户实际产品是否涉及召回','未做标准化缺陷原因分类，风险标签不能替代原因排名']}
dump(ROOT/'annual-2025-reviewed.json',annual);dump(ROOT/'recalls-2025-reviewed.json',unique);dump(ROOT/'review-ledger-2025.json',ledger);dump(ROOT/'quality-report-2025.json',report)
for filename,var,data in [('annual-2025-reviewed.js','recallAnnual2025',annual),('dataset-2025.js','recallDataset',unique)]:
    (ROOT.parent/'dist'/filename).write_text('const '+var+' = '+json.dumps(data,ensure_ascii=False)+';\n',encoding='utf-8')
with (ROOT/'recalls-2025-reviewed.csv').open('w',encoding='utf-8-sig',newline='') as f:
    fields=['id','published_date','product_name','category','risk_tags','model_raw','production_dates_raw','batch_raw','scope_assessment','quantity','quantity_unit','source_url','reviewed_at']
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
    for r in unique:w.writerow({k:'；'.join(r[k]) if isinstance(r.get(k),list) else r.get(k) for k in fields})
with sqlite3.connect(ROOT/'recalls-2025.sqlite3') as db:
    db.execute('CREATE TABLE IF NOT EXISTS notices(id TEXT PRIMARY KEY,published_date TEXT,product_name TEXT,category TEXT,source_url TEXT,record_json TEXT)');db.execute('DELETE FROM notices')
    db.executemany('INSERT INTO notices VALUES(?,?,?,?,?,?)',[(r['id'],r['published_date'],r['product_name'],r['category'],r['source_url'],json.dumps(r,ensure_ascii=False)) for r in unique])
sys.stdout.reconfigure(encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
