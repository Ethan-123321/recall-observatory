/* Three-valued, source-preserving scope evaluation. No model makes the decision. */
const RecallVerify=(()=>{
 const version='scope-v4';
 const norm=s=>String(s??'').normalize('NFKC').toUpperCase().replace(/\s+/g,'').replace(/[‐‑–—]/g,'-');
 const date=s=>{if(!/^\d{4}-\d{2}-\d{2}$/.test(s||''))return null;const d=new Date(s+'T00:00:00Z');return Number.isFinite(+d)&&d.toISOString().slice(0,10)===s?s:null};
 const pad=x=>String(x).padStart(2,'0');
 function period(y,m,d){const start=`${y}-${pad(m)}-${d?pad(d):'01'}`;if(!date(start))return null;const end=d?start:new Date(Date.UTC(+y,+m,0)).toISOString().slice(0,10);return {start,end,precision:d?'day':'month'};}
 function dateSpec(raw){
  let s=norm(raw).replace(/[.．/]/g,'-').replace(/起(?=至)/g,'').replace(/止$/,'');
  const shortDay=s.match(/^(\d{4})年(\d{1,2})月(\d{1,2})日[至到~～-](\d{1,2})日$/);
  if(shortDay)s=`${shortDay[1]}年${shortDay[2]}月${shortDay[3]}日至${shortDay[1]}年${shortDay[2]}月${shortDay[4]}日`;
  const short=s.match(/^(\d{4})年(\d{1,2})月?[至到~～-](\d{1,2})月$/);
  if(!short&&(s.match(/月/g)||[]).length>1&&(s.match(/\d{4}年/g)||[]).length===1)return null;
  if(short)s=`${short[1]}年${short[2]}月至${short[1]}年${short[3]}月`;
  s=s.replace(/月(?=[至到~～-]|$)/g,'').replace(/年|月/g,'-').replace(/日/g,'').replace(/-(?=[至到~～、,，;；]|$)/g,'');
  const tokens=[...s.matchAll(/(\d{4})-(\d{1,2})(?:-(\d{1,2})(?!\d))?(?!\d)/g)];
  if(!tokens.length)return null;
  const points=tokens.map(m=>period(m[1],m[2],m[3]));if(points.some(p=>!p))return null;
  const residue=s.replace(/\d{4}-\d{1,2}(?:-\d{1,2}(?!\d))?(?!\d)/g,'#');
  let ranges;
  if(residue==='#')ranges=[[points[0].start,points[0].end]];
  else if(/^#[至到~～-]#$/.test(residue)&&points.length===2&&points[0].start<=points[1].start)ranges=[[points[0].start,points[1].end]];
  else if(/^#([、,，;；]#)+$/.test(residue))ranges=points.map(p=>[p.start,p.end]);
  else return null;
  return {raw:String(raw),precision:points.every(p=>p.precision==='day')?'day':points.every(p=>p.precision==='month')?'month':'mixed',ranges};
 }
 function dates(raw){const s=dateSpec(raw);return s?.precision==='day'?s.ranges:null;}
 function models(raw){
  const text=String(raw||'').normalize('NFKC').trim(),s=norm(text);
  // Explicit single-label formats: keep the whole specification, never invent aliases.
  const literal=/^\d{2,3}\/\d{2,3}[A-Z]\s+[A-Z]{1,3}$/i.test(text)||/^[A-Z0-9-]+\s+\d+(?:\.\d+)?(?:mm|cm|W)$/i.test(text)||/^[A-Z0-9-]+\s*明装$/i.test(text)||/^[A-Z0-9.*×/+-]+\([A-Z0-9.*×/+-]+\)$/i.test(text)||/^\d+(?:\.\d+)?(?:G|克|ML|毫升|L|升)\/(?:包|盒|袋|瓶|罐)$/i.test(text)||/^\d+(?:[.*×]\d+)+(?:mm|cm)[*×]\d+页$/i.test(text);
  if(literal)return [s];
  if(/[A-Za-z0-9]\s+[A-Za-z0-9]/.test(text))return null;
  return s&&s.length<180&&!/^[-/*×.]+$/.test(s)&&/^[A-Z0-9.*×/+\-、,，;；]+$/.test(s)?s.split(/[、,，;；]/).filter(Boolean):null;
 }
 function batches(raw){const s=norm(raw);if(/^\d{4}\/\d{1,2}\/\d{1,2}$/.test(s)&&dateSpec(s))return [s];if(!s||/未|无|不详|见|批次|批号|至|到|\/|\(|（|\*|X{2}/.test(s)||/^[-.]+$/.test(s))return null;const values=s.split(/[、,，;；]/);if(values.some(x=>/^[A-Z]*\d{3,}-[A-Z]+\d{3,}$|^\d{6,}-\d{6,}$|^([A-Z]+)\d+-\1\d+$/.test(x)))return null;return /^[A-Z0-9\-、,，;；]+$/.test(s)?values:null;}
 const supported=r=>['按型号与生产日期界定','明确限定范围内全部批次','需同时核对批次','离散日期或批次分别界定','多型号分别界定'].includes(r.scope_assessment);
 function conflicts(r){return [...(r.quality_flags||[]),r.scope_rules?.conflict||''].filter(t=>/冲突|笔误|模糊|待确认|不完整|倒置|无法.*区分/.test(t));}
 function groups(r){
  const rules=r.scope_rules,source=rules?.groups||r.scope_details?.groups;
  const grouped=Array.isArray(source)&&source.length>0;
  const noBatch=r.scope_assessment==='按型号与生产日期界定'&&!r.batch_raw;
  const allBatch=r.scope_assessment==='明确限定范围内全部批次'&&/全部/.test(r.batch_raw||'');
  return (grouped?source:[{model:r.model_raw,source_dates:r.production_dates_raw,batch_raw:r.batch_raw}]).map((g,i)=>{
   const modelRaw=g.model_raw??g.model??'',dateRaw=g.source_dates??g.production_dates_raw??'',batchRaw=g.batch_raw??(g.batches||[]).join('、');
   const required={model:true,production:true,batch:!(noBatch||allBatch),...(rules?g.required||{}:{})};
   const spec=dateSpec(dateRaw);
   const explicit=r.domain==='汽车'&&rules?.method==='source-bound-normalization-v1'&&Array.isArray(g.model_values)&&g.model_values.length===1&&g.model_values[0]===modelRaw&&g.evidence?.includes(modelRaw)?g.model_values.map(norm):null;
   return {id:String(g.group_id||`${r.id||'notice'}:g${i+1}`),models:explicit||models(modelRaw),dateSpec:spec,dateRanges:spec?.ranges||null,batchValues:batches(batchRaw),modelRaw,dateRaw,batchRaw,required,grouped,evidence:g.evidence||'',exclusions:g.exclusions||[],unresolved:!!g.unresolved||/可含子组|对应关系.*未|未.*关联/.test(g.evidence||''),allBatch};
  });
 }
 function scopeInfo(r){
  const gs=groups(r),status=r.scope_details?.status||'';
  const ambiguous=/型号缺失|批次不完整|对应关系|日期冲突|未逐项关联|未明确逐项对应|未明确逐项|不按顺序猜配|不能跨型号|原文第\d+组/.test(status)||gs.some(g=>g.unresolved||/原文第\d+组/.test(g.modelRaw));
  const complete=(r.scope_rules?r.scope_rules.complete===true:supported(r)&&!ambiguous)&&!gs.some(g=>g.unresolved);
  const executable=gs.every(g=>(!g.required.model||g.models)&&(!g.required.production||g.dateSpec)&&(!g.required.batch||g.batchValues)&&!g.exclusions.length);
  return {groups:gs,complete,executable,conflicts:conflicts(r),version};
 }
 const actions={missing_model:'请查看机身铭牌、包装或说明书中的完整型号 / 规格。',invalid_production:'日期无效，请填写真实的YYYY-MM-DD或YYYY-MM。',missing_production:'请查看产品标签的生产日期；不要使用购买日期。',missing_batch:'请查看产品底部或包装标签中的“批次 / LOT / SN”字段。',unsupported_model:'型号或规格尚未建立明确规则，请查看原文对应产品。',unsupported_production:'原文日期精度、开放区间或关联关系尚不明确，请查看范围原文。',unsupported_batch:'公告批号缺失或存在简称，请查阅原文，并通过公告提供的渠道核实。',date_precision:'请补充到日的生产日期；当前月份与公告范围只有部分重叠。',unresolved_scope:'尚有未明确的范围或条件组，请结合原文确认型号、日期与批次的对应关系。',exclusion_unknown:'请补充排除条件所需的信息，或查看公告中的例外说明。',conflict:'请对照下方疑点与原文，通过公告提供的联系方式确认。',vin:'目前完成车型与日期初筛，请通过厂家官方渠道核对VIN。'};
 function compareDate(input,spec){
  const given=/^\d{4}-\d{2}(?:-\d{2})?$/.test(input||'')?dateSpec(input):null;
  if(!given||!spec)return 'unknown';
  const [a,b]=given.ranges[0],ranges=[...spec.ranges].sort((x,y)=>x[0].localeCompare(y[0]));
  let cursor=a;
  for(const [start,end] of ranges){if(end<cursor)continue;if(start>cursor)break;if(end>=b)return 'yes';cursor=new Date(Date.parse(end+'T00:00:00Z')+86400000).toISOString().slice(0,10);}
  return ranges.every(([start,end])=>end<a||start>b)?'no':'unknown';
 }
 function evidence(r,g,field,excerpt){return {url:r.source_url||'',sha256:r.sha256||'',locator:`条件组 ${g.id} · ${field}`,excerpt:String(excerpt||''),context:g.evidence||''};}
 function conditions(r,g,input){
  return [['model','型号 / 规格',g.modelRaw,g.models],['production','生产日期',g.dateRaw,g.dateSpec],['batch','批号 / 序列号',g.batchRaw,g.batchValues]].map(([key,label,raw,parsed])=>{
   const value=String(input[key]||'').trim(),valid=key==='production'?/^\d{4}-\d{2}(?:-\d{2})?$/.test(value)&&dateSpec(value):value;
   const state=!g.required[key]?'na':!valid||!parsed?'unknown':key==='production'?compareDate(value,parsed):parsed.includes(norm(value))?'yes':'no';
   const code=state==='unknown'?(!parsed?'unsupported_'+key:!valid?(key==='production'&&value?'invalid_production':'missing_'+key):'date_precision'):null;
   const basis=r.scope_rules?.groups?.find(x=>(x.group_id||'')===g.id)?.batch_basis;
   const reason=state==='na'?(key==='batch'&&basis?basis:key==='batch'&&g.allBatch?'公告限定型号与生产期内全部批次':'本组不要求另核对此条件'):code?actions[code]:key==='production'?'依据原文精度比较；离散日期保留间隔':'按完整值比较，不将简称或相似值当作相同';
   return {key,label,value:value||'未提供',source:raw||'公告未明确列出',state,reason,code,group_id:g.id,evidence:evidence(r,g,label,raw),precision:key==='production'?g.dateSpec?.precision:null};
  });
 }
 function exclusions(r,g,input,list){
  if(!Array.isArray(list))return [{state:'unknown',code:'exclusion_unknown',label:'排除条件',value:'',source:String(list),reason:actions.exclusion_unknown,evidence:evidence(r,g,'排除条件',list)}];
  return list.map((e,i)=>{
   const defined=e&&typeof e==='object'&&['model','model_raw','source_dates','batches','batch_raw'].some(k=>e[k]);
   if(!defined)return {state:'unknown',code:'exclusion_unknown',label:'排除条件',source:typeof e==='string'?e:JSON.stringify(e),reason:actions.exclusion_unknown,evidence:evidence(r,g,'排除条件',typeof e==='string'?e:JSON.stringify(e))};
   const ex={...g,id:g.id+':exclude'+(i+1),modelRaw:e.model_raw||e.model||'',dateRaw:e.source_dates||'',batchRaw:e.batch_raw||(e.batches||[]).join('、')};
   ex.models=models(ex.modelRaw);ex.dateSpec=dateSpec(ex.dateRaw);ex.batchValues=batches(ex.batchRaw);ex.required={model:!!ex.modelRaw,production:!!ex.dateRaw,batch:!!ex.batchRaw};
   const rows=conditions(r,ex,input),state=rows.some(x=>x.state==='no')?'no':rows.every(x=>['yes','na'].includes(x.state))?'yes':'unknown';
   return {state,code:state==='unknown'?'exclusion_unknown':null,label:'排除条件 '+(i+1),source:e.evidence||[ex.modelRaw,ex.dateRaw,ex.batchRaw].filter(Boolean).join(' ＋ '),reason:state==='yes'?'输入符合此排除条件':state==='no'?'输入不符合此排除条件':actions.exclusion_unknown,rows,evidence:evidence(r,ex,'排除条件',e.evidence||JSON.stringify(e))};
  });
 }
 function check(r,input={}){
  const info=scopeInfo(r),gs=info.groups;
  const groupResults=gs.map(g=>{
   const rows=conditions(r,g,input),exceptions=exclusions(r,g,input,g.exclusions);
   const state=rows.some(x=>x.state==='no')||exceptions.some(x=>x.state==='yes')?'outside':g.unresolved||rows.some(x=>x.state==='unknown')||exceptions.some(x=>x.state==='unknown')?'pending':'matched';
   return {...g,rows,exceptions,state};
  });
  const globalExclusions=exclusions(r,{id:'notice',evidence:''},input,r.scope_rules?.exclusions||[]);
  const unresolvedExclusion=!r.scope_rules&&/排除|不包括|但不含|除外/.test([r.model_raw,r.production_dates_raw,r.batch_raw,r.scope_details?.status].join(' '));
  let state=groupResults.some(g=>g.state==='matched')?'matched':info.complete&&groupResults.every(g=>g.state==='outside')?'outside':'pending';
  if(globalExclusions.some(x=>x.state==='yes'))state='outside';
  if(state==='matched'&&(!info.complete||globalExclusions.some(x=>x.state==='unknown')||unresolvedExclusion))state='pending';
  if(info.conflicts.length)state='pending';
  const screening=state;if(r.domain==='汽车'&&state==='matched')state='pending';
  const relevant=state==='matched'?groupResults.filter(g=>g.state==='matched'):groupResults.filter(g=>g.state!=='outside');
  const codes=new Set();
  if(state==='pending'){
   relevant.forEach(g=>{g.rows.forEach(x=>{if(x.code)codes.add(x.code)});g.exceptions.forEach(x=>{if(x.code)codes.add(x.code)})});
   if(!info.complete||gs.some(g=>g.unresolved))codes.add('unresolved_scope');
   if(globalExclusions.some(x=>x.state==='unknown')||unresolvedExclusion)codes.add('exclusion_unknown');
   if(info.conflicts.length)codes.add('conflict');
   if(r.domain==='汽车')codes.add('vin');
  }
  const primary=relevant[0]||groupResults[0];
  const carPreMatch=r.domain==='汽车'&&!info.conflicts.length&&groupResults.some(g=>g.state==='matched');
  const title=carPreMatch?'车型与生产日期符合初筛条件，待VIN核实':{matched:'符合该公告列明的范围条件',outside:'不符合该公告列明的范围条件',pending:'信息不足，暂无法确认'}[state];
  const missing=[...new Set(relevant.flatMap(g=>g.rows.filter(x=>x.code?.startsWith('missing_')).map(x=>x.label)))];
  const reason=state==='matched'?`已满足条件组 ${groupResults.flatMap((g,i)=>g.state==='matched'?[i+1]:[]).join('、')} 的全部条件，且未命中已列排除条件。`:state==='outside'?(globalExclusions.some(x=>x.state==='yes')?'输入命中公告排除条件。':'公告各组均有明确不符合的条件；未跨组拼接型号、日期或批次。'):missing.length?'还需补充：'+missing.join('、')+'。':r.domain==='汽车'?'车型与生产日期仅供初筛，仍需核对VIN。':'已保留不能确定的范围、精度或原文疑点。';
  const sourceGaps=[...new Set(relevant.flatMap(g=>g.rows.filter(x=>x.code?.startsWith('unsupported_')).map(x=>x.label)))];
  const guidance={userMissing:missing,sourceGaps,contact:r.contact_raw||'',vinUrl:r.domain==='汽车'?'https://www.samrdprc.org.cn/fzlm/qxqczhfwcx/index.html':null,carPreMatch};
  return {notice:r,rows:primary.rows,state,title,reason,guidance,nextSteps:[...codes].map(code=>({code,text:actions[code]})),note:r.domain==='汽车'?'车型与生产日期仅供初筛；具体车辆须通过厂家官方渠道核对VIN。':r.batch_review_note||'请结合公告原文与所列处理方式操作。',groups:gs,groupResults,globalExclusions,conflicts:info.conflicts,reasonCodes:[...codes],decisiveGroupIds:groupResults.filter(g=>g.state===(state==='matched'?'matched':'outside')).map(g=>g.id),scopeComplete:info.complete,screening,ruleVersion:version};
 }
 function search(rows,q,domain='全部',model=''){
  const terms=String(q).trim().split(/\s+/).map(norm).filter(Boolean),m=norm(model);
  return rows.filter(r=>(domain==='全部'||r.domain===domain)&&terms.every(t=>{const text=norm([r.title,r.product_name,r.producer,r.brand,r.model_raw].join(' '));const aliases={'充电宝':['充电宝','移动电源'],'电瓶车':['电瓶车','电动自行车']};return (aliases[t]||[t]).some(x=>text.includes(x))})&&(!m||norm([r.model_raw,...groups(r).map(g=>g.modelRaw)].join(' ')).includes(m))).sort((a,b)=>String(b.published_date||'').localeCompare(String(a.published_date||'')));
 }
 return {version,norm,date,dates,dateSpec,compareDate,models,batches,groups,scopeInfo,search,check};
})();
if(typeof module!=='undefined')module.exports=RecallVerify;
