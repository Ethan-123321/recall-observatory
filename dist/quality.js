/* One audit policy shared by the browser and the reproducible Node export. */
const RecallQuality=(()=>{
 const version='quality-v3';
 const statuses=['可直接使用','原文有信息，尚未整理','公告未披露','原文存在歧义或冲突','不适用','待审计'];
 const capabilities=['可进行确定性条件比对','可进行部分条件比对','仅支持检索与原文查阅'];
 const fields={producer:'企业',brand:'品牌',product_name:'产品名称',model_raw:'型号 / 规格',production_dates_raw:'生产日期',batch_raw:'批号 / 序列号',defect_raw:'缺陷',consequence_raw:'可能后果',remedy_raw:'处理方式',contact_raw:'联系方式'};
 function audit(r,v){
  const info=v.scopeInfo(r),gs=info.groups,flags=(r.quality_flags||[]).filter(x=>/冲突|笔误|模糊|待确认|不完整|无法.*辨|倒置/.test(x));
  const noBatch=r.scope_assessment==='按型号与生产日期界定'&&!r.batch_raw;
  const allBatch=r.scope_assessment==='明确限定范围内全部批次'&&/全部/.test(r.batch_raw||'');
  const result={};
  for(const [key,label] of Object.entries(fields)){
   const raw=r[key]||'',review=r.field_review?.[key]||{},legacy=r.review_evidence?.[key];
   const text=String(review.evidence||legacy||'');
   const hashOK=!!r.sha256&&(!review.source_sha256||review.source_sha256===r.sha256);
   const evidence=text&&hashOK?{url:r.source_url,sha256:r.sha256,locator:'现有字段复核记录：'+key,excerpt:text,method:review.status||'既有AI辅助文本复核'}:null;
   const range=['model_raw','production_dates_raw','batch_raw'].includes(key);
   let status='待审计',reason='尚无充分字段级证据，不能由空值推断公告未披露';
   if(raw){status='原文有信息，尚未整理';reason='已有摘录，仍需确认语义、结构化结果与原文对应关系'}
   // Ambiguous historical missing-field labels must not become confirmed non-disclosure.
   if(!raw&&review.status==='公告未明确披露，保留缺失'&&hashOK){status='公告未披露';reason='既有字段级复核明确记录未披露；非本轮重新查阅原文'}
   if(key==='batch_raw'&&noBatch&&!flags.length){status='不适用';reason='既有范围复核明确按型号与生产日期界定；不是由批号空白单独推断'}
   let normalized=null;
   if(key==='model_raw')normalized=v.models(raw);
   else if(key==='production_dates_raw')normalized=v.dateSpec(raw);
   else if(key==='batch_raw')normalized=allBatch?'公告限定范围内全部批次':v.batches(raw);
   else normalized=raw||null;
   if(range&&!normalized&&info.complete&&gs.length>1){
    const parsed=gs.map(g=>({group_id:g.id,value:key==='model_raw'?g.models:key==='production_dates_raw'?g.dateSpec:g.batchValues}));
    if(parsed.every(g=>g.value))normalized=parsed;
   }
   if(raw&&evidence&&normalized&&status!=='不适用'){
    status='可直接使用';reason=range?'字段级证据存在且当前解析器支持此格式；组间关联另行审计':'已有字段级证据与文本值；不代表人工专家认证';
   }
   if(review.source_sha256&&review.source_sha256!==r.sha256){status='原文存在歧义或冲突';reason='字段证据哈希与当前正文版本不一致'}
   if(range&&(flags.length||/无法可靠|不完整|无法.*区分/.test(review.status||''))){status='原文存在歧义或冲突';reason=[...flags,review.status||''].filter(Boolean).join('；')}
   result[key]={label,raw_value:raw||null,normalized_value:normalized,status,reason,evidence,review_status:review.status||r.review_status||'未记录',review_method:review.status|| (legacy?'既有AI辅助文本复核':'尚未完成字段级审计')};
  }
  const rangeReady=['model_raw','production_dates_raw','batch_raw'].every(k=>['可直接使用','不适用'].includes(result[k].status));
  const sourceReady=!!r.source_url&&!!r.sha256&&(rangeReady||gs.every(g=>g.evidence));
  const complete=info.complete&&info.executable&&sourceReady&&!info.conflicts.length&&r.domain!=='汽车';
  const structuredPartial=r.scope_rules?.source_sha256===r.sha256&&gs.some(g=>g.models&&g.dateSpec&&g.evidence);
  const partial=structuredPartial||['model_raw','production_dates_raw','batch_raw'].some(k=>result[k].status==='可直接使用');
  const capability=capabilities[complete?0:partial?1:2];
  const reasons=[];
  if(r.domain==='汽车')reasons.push('仅能初筛，具体车辆需官方核对VIN');
  if(!info.complete)reasons.push('公告范围或条件组关联仍有未明确项');
  if(!info.executable)reasons.push('型号或日期格式尚不能可靠执行');
  if(!sourceReady)reasons.push('决定性字段尚未整理、缺证据或存在疑点');
  if(!info.complete)reasons.push('现有范围分类仍要求补充确认');
  if(flags.length)reasons.push('范围含原文疑点，保留待确认');
  if(complete)reasons.push('条件组、范围证据与当前解析规则均可用；仍须用户提供完整信息');
  return {id:r.id,domain:r.domain,year:r.year,source:r.source_organization||new URL(r.source_url).hostname,source_url:r.source_url,sha256:r.sha256,reviewed_at:r.scope_reviewed_at||r.reviewed_at||null,policy_version:version,capability,reasons,fields:result};
 }
 const counts=(rows,key)=>Object.fromEntries([...new Set(rows.map(key))].sort().map(k=>[k,rows.filter(r=>key(r)===k).length]));
 function summary(rows){return {count:rows.length,policy_version:version,by_capability:counts(rows,r=>r.capability),by_domain:counts(rows,r=>r.domain),by_year:counts(rows,r=>r.year),by_source:counts(rows,r=>r.source),fields:Object.fromEntries(Object.keys(fields).map(k=>[k,Object.fromEntries(statuses.map(s=>[s,rows.filter(r=>r.fields[k].status===s).length]))]))};}
 function csv(rows){const quote=x=>'"'+String(x??'').replace(/"/g,'""')+'"';return '\ufeff'+[['公告ID','领域','年份','核验能力','分类原因','字段','字段状态','原因','原文摘录','来源','证据定位','规则版本'],...rows.flatMap(r=>Object.entries(r.fields).map(([k,f])=>[r.id,r.domain,r.year,r.capability,r.reasons.join('；'),k,f.status,f.reason,f.evidence?.excerpt||'',r.source_url,f.evidence?.locator||'',version]))].map(row=>row.map(quote).join(',')).join('\r\n');}
 return {version,statuses,capabilities,fields,audit,summary,csv};
})();
if(typeof module!=='undefined')module.exports=RecallQuality;
