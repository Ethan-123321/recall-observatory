"""Explicit, per-notice AI-assisted source review. Not human expert certification."""
import re, json
from pathlib import Path
CATEGORIES={'H':'家用电器','P':'个护电器','S':'防护消防用品','W':'文具','C':'服饰鞋包','F':'家具家居','T':'玩具','K':'食品接触用品','L':'照明电器','B':'婴童用品','E':'电源电器','J':'饰品','O':'光学用品','V':'电动自行车','D':'无人机','G':'日用清洁用品','Y':'运动用品','R':'燃气器具'}
RISKS={'e':'触电','f':'火灾/燃烧','s':'窒息/误吞','c':'割伤/刺伤','b':'烫伤','h':'化学健康风险','m':'机械伤害','a':'听力损伤','x':'爆炸','p':'防护失效','u':'未明确具体伤害','v':'视力影响','z':'空域及公共安全','i':'皮肤刺激/过敏','g':'微生物污染','t':'一氧化碳中毒'}
SCOPES={'E':'明确批次标识','L':'多个明确批次','A':'限定产品范围内全部批次','N':'未提供有效批次标识','U':'批次表述不完整','M':'多型号日期或批次分别对应','D':'多个离散生产日期'}
# Source fields were read for every entry; codes here are explicit review decisions.
REVIEW='''
113609 H u L
113608 P u E
113607 S p U
113605 W c N
113573 H e E
113565 C h E
113531 C m E
113517 F h U
113509 T h E
113508 T s E
113507 T s E
113506 T c E
113505 T a E
113504 T sc E
113496 K h E
113439 F h U
113423 C h E
113422 C h E
113494 P e U
113478 W h E
113477 W c N
113476 S mp E
113435 T bf E
113433 T m D
113432 T s E
113431 T s E
113430 T c E
113415 C ms E
113183 T s U
113211 L e U
113210 L ef M
113209 L e M
113167 P u E
113166 B c E
113165 L f E
113171 E e E
113123 S u M
113181 C m U
113190 H ef E
113188 H e E
113186 H e E
113184 S mp U
113180 C h E
113111 F h A
113091 H u N
113067 J s E
113066 W h U
113058 T h U
113033 E fx E
113023 H e E
113022 E e E
113020 L e M
113019 B m E
113000 F m L
115447 H e E
115415 T m E
115414 T s E
115413 T s E
115412 T sb E
115411 T ms E
115410 T a E
115427 S mp E
115167 H e E
115145 T c U
115143 T sh N
115148 T c E
115147 T s E
115146 T s E
115142 T m E
115133 E e N
115091 F h E
115083 E e N
115082 E b N
115052 F h E
115059 F m E
115057 H ef E
113927 W v E
113923 H e N
113922 H e N
113941 C h U
113940 C h N
113939 C h E
113929 E e U
113928 C s U
113918 F m E
113917 F h E
113916 P b E
113915 F m E
113914 H e E
113913 E f E
113921 H e E
113863 O v E
114126 H e E
114061 L e E
114058 C h N
114057 V fx N
114056 F m N
114035 D z L
114034 D z M
114033 D z E
114031 H e E
114030 H e E
113986 W v N
113999 C h U
113998 C h N
113997 C h E
113978 C ch E
113963 F hm E
'''
REVIEW += '''
115363 C m N
115361 G c E
115338 C h E
115337 T u N
115336 T u N
115335 T a E
115328 H e N
115326 C h E
115404 C h E
115403 P ef E
115402 K h E
115401 K h E
115400 C h E
115396 K m E
115393 G i U
115271 C m E
115268 H bef U
115266 H m E
115240 C h U
115239 W h E
115238 W h E
115237 W h E
115310 J h U
115308 E ef E
115307 S p M
115292 S mp U
115282 C h N
115281 C h N
115280 C h N
115183 S p N
115182 H e N
115181 H e U
115180 C m N
115179 H e U
115178 H e N
115170 H e N
115169 C m E
115168 C m N
115223 S p L
115222 T u E
115198 T m N
115197 T s E
115192 T s E
114962 Y h N
114921 T c E
114920 T ms N
114919 T bx N
115046 H e E
115032 K h E
115007 H e U
114997 S mp E
114996 E e E
114964 G s E
114963 C h N
81527d5795c84ba9b4618de7cb5b2e08 T c E
99af411bb0964ee38a4a5ded37915fa2 T h E
521eeb3613834b18b0d29ef72210e097 L e E
16716c3457b34a01b6b0aa7e5d8838d1 H e E
fe32a0c710844a099074e639440a8f40 F u E
'''

NOTES={
 '114587':'两型号数量分别为33000包、56400包；公告列出的四批次未明确与两型号逐项对应，不按顺序配对。',
 '114605':'原公告型号栏为斜杠，保留缺失值；需结合产品外观、名称、批次与厂家信息确认，不能虚构型号。',
 '114425':'三款鞋的数量分别为6、50、5双；型号、三个日期段和合同批次缺少明确逐项关联，不凭排列顺序配对。进度原文含2025年11月31日，该日期无效，需厂家确认，不能自动纠正。',
 '115623':'批次原文2025.9.1与生产日期2023.9.1—2023.10.10分别保留；批号形似日期不证明日期冲突，也不自动改写。',
 '114643':'两款裙共用所列日期范围；绳带风险对应燕舞欢欣连衣裙，pH问题对应蝶舞韶华汉服裙，公告层面保留多风险。',
 '114603':'三个原文批次按集合保留；批号形似日期不改写生产日期。',

 '115179':'两个型号与两个生产日的逐项对应未明确，不能按排列顺序推断映射；需补充厂家说明。',
 '115307':'三组型号、生产日期和批次分别对应；同一型号TZL30A出现两段日期，不能合并为连续范围。',
 '115280':'两型号共用所列生产日期，数量分别为240个、100个，合计340个。',
 '115183':'保留500袋为统计单位，每袋10枚是包装关系，不在总数中重复累加。',
 '114964':'保留11900盒为统计单位，每盒25支不另行叠加；误食风险不代表已发生事故。',
 '115396':'抗热震性不足导致破裂伤害，归机械伤害，不直接标记为爆炸。',
 '114034':'SG107MAX与SG107MAX2分别对应独立日期和批次；20台与5台不能与另一型号交换。',
 '113986':'三种纸雕本共用规格及生产日期，批次未列明，不能凭书名之外的信息直接确定。',
 '113978':'批次字段混合生产日和货号D6005，保留二者角色，货号不能当成日期。',

 '113929':'批次20231124X01--20231124X30是带前缀序号范围；前导零及前缀必须保留。不得把它解释成日期范围。',
 '113941':'批次字段写的是货号X2019011，不足以作为生产批次凭证。',
 '113928':'批次字段写的是货号3995035，不足以作为生产批次凭证。',
 '115145':'批次仅写2024年，不能认定2024年所有产品都涉及召回。',
 '115167':'原日期2025年10月20日-27日，省略的结束年月沿用2025年10月；批号2577#保留井号。',
 '113939':'两位年份23年按公告上下文为2023年，原文仍保留；批号007中必须保留前导零和中文。',
 '115411':'绳索缠绕颈部造成勒死风险，归绳索机械伤害及窒息，不归锐利边缘。',

 '113607':'灭火剂性能不足属于防护失效，不能标为产品自身起火；批次20220601/--含占位符，不扩展为完整日期区间。',
 '113605':'多款削笔机共用公告范围；起始月份精度不足，不能推定6月某日。未列批次不等于全部批次。',
 '113494':'三款产品、生产日期2023.3至今；“今”不可替换为采集日。批次反斜杠不是有效标识。',
 '113211':'公告日期自2019-11开始，但批次列表含201910-021，存在范围冲突；禁止自动肯定命中。',
 '113433':'2021-03-26和2021-06-12是两个离散日，不能合并成连续范围。',
 '113210':'四型号分别对应四个生产日；4批次只是数量，没有给出四个批次编码。',
 '113209':'四型号各自对应日期范围和批次编码；仅在相同型号内匹配，禁止跨型号组合。',
 '113123':'1500型号对应2024年2月和4月及两批次日；2000型号对应2023-07-23，不能共用外包日期区间。',
 '113184':'两种头盔在原表型号均写SJ-210，但批次写2批次；不能自行编造第二型号或第二批次。',
 '113020':'15W和28W产品分别对应不同日期与月份批次，不能互换。',
 '113111':'全部批次只适用于公告所列尺寸颜色及生产日期的床笠，不适用于品牌全部产品。',
 '113476':'生产日期2024-01-15与批号20240117保留为两个字段；批号形似日期不能据此改写生产日期。',
 '113066':'原批次202201-202203是范围写法，保留月份精度，不擅自生成逐日批次。',
}

def apply_review(rows):
 scopes=json.loads((Path(__file__).parent/'scope-details.json').read_text(encoding='utf-8'))
 decisions={line.split()[0]:line.split()[1:] for line in REVIEW.strip().splitlines() if line.strip()}
 decisions.update(json.loads((Path(__file__).parent/'review-v5.json').read_text(encoding='utf-8')))
 for r in rows:
  suffix=r['id'].rsplit('_',1)[1]
  if suffix not in decisions:continue
  cat,risk,scope=decisions[suffix]
  r['category']=CATEGORIES[cat];r['risk_tags']=[RISKS[c] for c in risk]
  r['category_method']='per_notice_source_review_v2'
  r['risk_method']='defect_and_consequence_source_review_v2'
  r['review_status']='已完成逐条文本复核'
  r['reviewer']='AI-assisted source review; 非人工专家认证'
  r['reviewed_at']=r['retrieved_date']
  r['batch_review_status']=SCOPES[scope]
  r['batch_review_note']=NOTES.get(suffix,{
   'E':'批次按原文字面保留；形似日期的编码不替代生产日期。',
   'L':'按公告列出的批次集合核对，不以最小值与最大值生成连续区间。',
   'A':'全部批次仍受公告型号、规格与生产日期限制。',
   'N':'缺失或占位符不是有效批号；召回范围应结合型号、生产日期及正文判断。',
   'U':'范围记号、批次数或不完整标识不能直接作为批号匹配；是否需确认取决于整体范围。',
   'M':'不同型号的日期及批次关联需分别核验。',
   'D':'分别保留离散日期，不填充间隔。'}[scope])
  r['scope_assessment']='需同时核对批次'
  r['scope_assessment_reason']='公告给出了可识别的批次条件，应与型号、生产日期一起核对。'
  if scope=='A':
   r['scope_assessment']='明确限定范围内全部批次'
   r['scope_assessment_reason']='原文明确全部批次，但必须同时满足规格、颜色与日期条件。'
  elif scope in 'UN':
   # Explicit per-notice decisions: missing batch numbers alone do not imply missing scope.
   date_defined={'114586','114548','114621','114620','114606','114643','114640','114633','114381','114374','114362','114354','114436','114419','115610','115609','115468','115363','115337','115336','115328','115393','115268','115240','115310','115292','115282','115281','115280','115183','115182','115181','115180','115178','115170','115168','115198','114962','114920','114919','115007','114963','113607','113573','113183','113181','113091','113058','115143','115133','115083','115082','113923','113922','113941','113940','113928','114058','114057','114056','113986','113999','113998'}
   if suffix in date_defined:
    r['scope_assessment']='按型号与生产日期界定'
    r['scope_assessment_reason']='所列规格与生产日期可用于范围初筛；公告未提供额外可核对的批次编码。不能由批次栏缺失推断范围不明，也不能扩大为品牌全部产品。'
   else:
    r['scope_assessment']='范围细节需补充确认'
    r['scope_assessment_reason']='日期精度、开放结束日期、序号范围或多产品识别存在未确定细节；详见逐条复核说明。'
   r['batch_review_note']+=' 本次范围复核：'+r['scope_assessment_reason']
  elif scope=='M':
   r['scope_assessment']='多型号分别界定'
   r['scope_assessment_reason']='按型号分别使用对应日期和批次，不跨组拼接。'
  elif scope=='D':
   r['scope_assessment']='离散日期分别界定'
   r['scope_assessment_reason']='仅核对列明的生产日，不填充两个日期之间的间隔。'
  r['scope_reviewed_at']=max(r['retrieved_date'],'2026-10-18')
  r['review_evidence']={k:r[k] for k in ['product_name','model_raw','production_dates_raw','batch_raw','defect_raw','consequence_raw']}
  r['scope_details']=scopes.get(suffix)
  r['automated_match_enabled']=False
  r['quality_flags']=[f for f in r['quality_flags'] if f!='risk_requires_review']
  if r['scope_assessment']=='范围细节需补充确认':r['quality_flags'].append('scope_requires_manufacturer_confirmation')
  if risk=='u':r['quality_flags'].append('source_does_not_specify_harm')
 return rows
