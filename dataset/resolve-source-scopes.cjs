/* Exact local table extraction; no inferred aliases, blank-batch waiver, or guessed joins. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),v=require('../dist/verify.js');
const ROOT=__dirname,method='source-table-exact-v2';
const labels={model_raw:'型号/规格',production_dates_raw:'生产起止日期',batch_raw:'生产批号/批次'};
function splitItems(s){let depth=0,out=[],start=0;for(let i=0;i<s.length;i++){if(/[（(]/.test(s[i]))depth++;if(/[）)]/.test(s[i]))depth--;if(depth<0)return [];if(!depth&&/[、；;]/.test(s[i])){out.push(s.slice(start,i).trim());start=i+1;}}return depth?[]:[...out,s.slice(start).trim()];}
function namedBatches(found){
 const models=splitItems(found.model_raw.value),items=splitItems(found.batch_raw.value),dates=found.production_dates_raw.value;
 if(models.length<2||models.length!==items.length||!v.dateSpec(dates))return null;
 const groups=items.map(item=>{
  const m=item.match(/^(\d{4}\/\d{1,2}\/\d{1,2})[（(]([^（）()]+)[）)]$/);if(!m||!v.batches(m[1]))return null;
  const candidates=models.filter(x=>x.startsWith(m[2]));if(candidates.length!==1)return null;
  return {model:candidates[0],model_values:[candidates[0]],source_dates:dates,batch_raw:m[1],required:{model:true,production:true,batch:true},evidence:`型号/规格：${candidates[0]}；生产起止日期：${dates}；生产批号/批次：${item}`};
 });
 return groups.every(Boolean)&&new Set(groups.map(g=>g.model)).size===models.length?groups:null;
}
function literal(s){
 if(!s||s.length>180||/未|详|见|不详|或|至|到|全部|系列|等|型号|规格[:：]|[、,，;；]|\d+#?[-~～—]\d+/.test(s))return null;
 let depth=0;
 for(const c of s.normalize('NFKC')){if(c==='(')depth++;if(c===')')depth--;if(depth<0||(!depth&&/[、,，;；]/.test(c)))return null;}
 if(depth||/\d+[a-zA-Z]*\s+\d+[a-zA-Z]*/.test(s)&&!/(?:mm|cm|ml|W|V|Hz|张|片|页)/i.test(s))return null;
 if(/^[\s/\-]+$/.test(s))return null;
 return [s];
}
function apply(rows,inventory){
 for(const r of rows){
  const src=inventory[r.id];if(!src||src.sha256!==r.sha256)throw Error('Missing bound source '+r.id);
  const correction=JSON.parse(fs.readFileSync(path.join(ROOT,'scope-image-corrections-20261101.json'),'utf8'))[r.id];
  if(correction){
   const asset=src.assets.find(a=>a.sha256===correction.image_sha256);
   const bytes=fs.readFileSync(path.join(ROOT,correction.image_file));
   if(!asset||crypto.createHash('sha256').update(bytes).digest('hex')!==correction.image_sha256)throw Error('Unbound image '+r.id);
   r.scope_rules={method:'source-image-reviewed-v2',source_sha256:r.sha256,complete:true,image_sha256:correction.image_sha256,image_url:asset.url,groups:correction.groups.map((g,i)=>({...g,group_id:r.id+':image'+(i+1),locator:correction.image_file+' · '+correction.locator,required:{model:true,production:true,batch:true}})),note:'2026-11-01 AI逐项视觉核对原图范围三行；型号、日期、批次按原图名称关联；非人工或厂家确认。',review_state:{rule_processing:'逐组结构化',ai_review:'2026-11-01 AI视觉核对范围三行',human_review:'未人工复核'}};
   continue;
  }
  if(r.domain==='汽车'){
   const review=r.scope_review;
   if(review&&review.source_sha256!==r.sha256)continue;
   const day='\\d{4}年\\d{1,2}月\\d{1,2}日';
   const end='(?:\\d{4}年)?\\d{1,2}月\\d{1,2}日';
   const re=new RegExp(`(?:生产日期(?:为|从|在))?(${day})(?:[至到](${end}))?(?:期间)?(?:部分)?(?:生产的|生产|的)(?:\\d+辆)?([^，。；\\n]+?(?:车|车型|车辆|底盘|前控制臂))(?:[，,]\\s*(?:共计|共|计)|\\d+辆[；。])`,'g');
   const source=review?.evidence||r.production_dates_raw||src.text;
   const extracted=[...source.matchAll(re)].filter(m=>v.norm(src.text).includes(v.norm(m[0]))&&!/排除|除外|不包括|但不含/.test(m[0])).map(m=>({model:m[3],model_values:[m[3]],source_dates:m[1]+(m[2]?'至'+m[2]:''),batch_raw:'',required:{model:true,production:true,batch:false},evidence:m[0],locator:`${r.raw_file} · 范围段落 · ${m[0]}`})).filter(g=>v.dateSpec(g.source_dates));
   const previous=r.scope_rules?.groups||[],added=extracted.filter(g=>!previous.some(p=>v.norm(p.model)===v.norm(g.model)&&v.norm(p.source_dates)===v.norm(g.source_dates)));
   if(added.length)r.scope_rules={method,source_sha256:r.sha256,complete:false,groups:[...previous,...added].map((g,i)=>({...g,group_id:r.id+':screen'+(i+1)})),note:'逐句绑定车型描述与生产日期；已提取条款不声明覆盖全文，必须官方核对VIN。',review_state:{rule_processing:'本轮本地正文条款提取',ai_review:'沿用已记录的范围AI辅助复核',human_review:'本轮未人工复核'}};
   continue;
  }
  if(r.scope_rules)continue;
  const cells=src.cells,found={};
  for(const [field,label] of Object.entries(labels)){
   const hits=cells.flatMap((s,i)=>v.norm(s)===v.norm(label)?[i]:[]);
   if(hits.length===1)found[field]={value:cells[hits[0]+1],locator:`${r.raw_file} · td/th[${hits[0]+2}] · ${label}`};
  }
  if(Object.keys(found).length!==3)continue;
  // Named batch parentheticals bind to a unique FULL specification; never zip lists by position.
  const named=namedBatches(found);
  if(named&&Object.entries(found).every(([k,f])=>v.norm(f.value)===v.norm(r[k]))&&!/冲突|笔误|倒置|排除|疑似/.test((r.quality_flags||[]).join(' '))){
   const locator=Object.values(found).map(f=>f.locator).join('；');
   r.scope_rules={method,source_sha256:r.sha256,complete:true,groups:named.map((g,i)=>({...g,group_id:r.id+':named'+(i+1),locator})),note:'按批次括注产品名唯一匹配完整规格；生产期保留公告总区间，未将批号日期改写成生产日期。',review_state:{rule_processing:'HTML具名批次规则处理',ai_review:'本轮规则审阅，未逐条AI全文复核',human_review:'未人工复核'}};
   r.scope_processing={method,locator,source_sha256:r.sha256,processed_at:'2026-11-01',human_review:false};continue;
  }
  // No overriding unresolved relationships or source anomalies from earlier reviews.
  const concerns=[...(r.quality_flags||[]),r.scope_details?.status||'',r.scope_review?.note||''].join(' ');
  if(/冲突|笔误|倒置|缺失|未披露|不完整|未明确|未逐项|未.*对应|未.*关联|未给出|不按顺序|不自动|无法|待确认|需.*确认|不能|首批|排除|除外|不包括|但不含|疑似/.test(concerns))continue;
  if(!Object.entries(found).every(([k,f])=>v.norm(f.value)===v.norm(r[k])))continue;
  const model=found.model_raw.value,dates=found.production_dates_raw.value,batch=found.batch_raw.value;
  const modelValues=v.models(model)||literal(model),spec=v.dateSpec(dates),batchValues=v.batches(batch)||v.batchRange(batch);
  if(!modelValues||!spec||!batchValues)continue;
  if(modelValues.length>1&&(!(Array.isArray(batchValues)&&batchValues.length===1)||spec.ranges.length!==1))continue;
  const evidence=Object.entries(found).map(([k,f])=>`${labels[k]}：${f.value}`).join('；');
  const locator=Object.values(found).map(f=>f.locator).join('；');
  r.scope_rules={method,source_sha256:r.sha256,complete:true,groups:[{group_id:r.id+':table1',model,model_values:modelValues,source_dates:dates,batch_raw:batch,required:{model:true,production:true,batch:true},evidence,locator}],note:'本轮本地HTML表格规则处理；仅接受单一明确条件组，逐字段绑定原文位置；批号必须填写。',review_state:{rule_processing:'自动规则处理并校验本地源文件',ai_review:'本轮未逐条AI语义复核',human_review:'未人工复核'}};
  r.scope_processing={method,evidence,locator,source_sha256:r.sha256,processed_at:'2026-11-01',human_review:false};
 }
 return rows;
}
if(require.main===module){
 const rows=JSON.parse(fs.readFileSync(0,'utf8')),sources=JSON.parse(fs.readFileSync(path.join(ROOT,'scope-source-inventory.json'),'utf8'));
 process.stdout.write(JSON.stringify(apply(rows,sources)));
}
module.exports={apply,literal,namedBatches,splitItems};
