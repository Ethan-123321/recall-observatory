/* Derived rules from version-bound existing evidence. Never overwrites source fields. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const v=require('../dist/verify.js');
const method='source-bound-normalization-v1';
const corrections=JSON.parse(fs.readFileSync(path.join(__dirname,'scope-source-corrections.json'),'utf8'));
// 2026-10-25 visual checks of the original PDF first-page scope, not inferred from empty fields.
const foodChecks={
 fj_P020260115591615780613:{hash:'8e8f66d17f36cefa08097df84528c8b0a69adeab6121578c49b424c3c4f710d1',model:'250g/包',date:'2025-11-25',batch:'2025-11-25',evidence:'尚品佛跳墙，商标海香顺，规格250g/包，生产日期（批次）2025-11-25。'},
 fj_P020260115591192169632:{hash:'bd82be6a9127046d3207952923eebfce1cf172963319e4117ea517d5853c8190',model:'260克/盒',date:'2025-11-11',batch:'2025-11-11',evidence:'金汤佛跳墙，规格260克/盒，生产日期（批次）2025-11-11。'},
 fj_P020260115590795751838:{hash:'196216706e897b7a9d4f8dea4b78e0845f3498840d76ff6d1b0d03aa0766f867',model:'1.8L',date:'2025.11.05',batch:'2025/11/05',evidence:'食用植物调和油；生产日期2025.11.05；产品批次2025/11/05；商标金旺龙；规格1.8L。'}
};
function enrich(r){
 if(r.scope_rules)return r;
 const correction=corrections[r.id];
 if(correction){
  if(correction.source_sha256!==r.sha256)throw Error('Scope correction source changed '+r.id);
  r.scope_rules={...correction,method,review_method:correction.method,groups:correction.groups.map((g,i)=>({...g,group_id:r.id+':source'+(i+1),required:g.required||{model:true,production:true,batch:true}}))};
  return r;
 }
 const food=foodChecks[r.id];
 if(food){
  if(r.sha256!==food.hash||r.model_raw!==food.model||r.production_dates_raw!==food.date||r.batch_raw!==food.batch)throw Error('Food review changed '+r.id);
  r.scope_rules={method,source_sha256:r.sha256,complete:true,groups:[{model:food.model,source_dates:food.date,batch_raw:food.batch,required:{model:true,production:true,batch:true},evidence:food.evidence}],note:'2026-10-25核对原PDF第一页召回食品信息；AI视觉复核，非厂家认证。'};
  r.field_review={...r.field_review,...Object.fromEntries(['model_raw','production_dates_raw','batch_raw'].map(k=>[k,{status:'2026-10-25原PDF第一页AI视觉复核',evidence:food.evidence,source_sha256:r.sha256}]))};
  return r;
 }
 const review=r.scope_review,groups=r.scope_details?.groups;
 const bound=review?.source_sha256===r.sha256&&review?.status==='范围条件AI辅助复核';
 const risky=/型号[:：].*型号[:：]|冲突|笔误|倒置|缺失|未明确|未逐项|不完整|无法|排除|除外/;
 if(r.domain==='一般消费品'&&bound&&groups?.length&&!risky.test([review.note,r.scope_details.status,...groups.map(g=>g.quantity_raw||''),...(r.quality_flags||[])].join(' '))){
  // Keep each reviewed row intact; do not create any model/date cross product.
  if(groups.every(g=>v.models(g.model)?.length===1&&v.dateSpec(g.source_dates)&&v.batches(g.batch_raw)&&[g.model,g.source_dates,g.batch_raw].every(x=>typeof x==='string'&&review.evidence.includes(x)))){
   r.scope_rules={method,source_sha256:r.sha256,complete:true,groups:groups.map((g,i)=>({...g,group_id:r.id+':normalized'+(i+1),required:{model:true,production:true,batch:true},evidence:[g.model,g.source_dates,g.batch_raw].join('；')})),note:'逐组保留已有复核对应关系；组内三项同时满足，未解除批次条件，也未跨组拼接。'};
  }
 }
 if(r.domain==='汽车'&&bound&&review.evidence){
  const date='\\d{4}年\\d{1,2}月\\d{1,2}日';
  const regex=new RegExp(`(${date})至(${date})(?:期间)?生产的([^，。；\\n]+?汽车)[，,](?:共计|共|计)`,'g');
  const extracted=[...review.evidence.matchAll(regex)].filter(m=>v.dateSpec(m[1]+'至'+m[2])&&!/除外|不包括|但不含/.test(m[0])).map((m,i)=>({group_id:r.id+':screen'+(i+1),model:m[3],model_values:[m[3]],source_dates:m[1]+'至'+m[2],batch_raw:'',required:{model:true,production:true,batch:false},evidence:m[0]}));
  // Extracted clauses may be only a subset: never assert completeness or a final VIN result.
  if(extracted.length)r.scope_rules={method,source_sha256:r.sha256,complete:false,groups:extracted,note:'按原文同一句提取车型描述与生产区间，仅支持已提取条款的初筛；未声明完整覆盖，须核对VIN。'};
 }
 return r;
}
function build(rows){
 for(const r of rows){
  if(!r.raw_file)continue;
  const file=path.resolve(__dirname,r.raw_file.replaceAll('\\','/'));
  if(!file.startsWith(__dirname+path.sep)||!fs.existsSync(file))throw Error('Missing source '+r.id);
  if(crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex')!==r.sha256)throw Error('Source changed '+r.id);
  enrich(r);
 }
 return rows;
}
if(require.main===module)process.stdout.write(JSON.stringify(build(JSON.parse(fs.readFileSync(0,'utf8')))));
module.exports={enrich,build};
