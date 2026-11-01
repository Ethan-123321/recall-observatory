/* Compile source-bound earlier AI transcriptions into executable groups.
 * This reuses named-field evidence and verified cached images; it does not relabel a notice.
 */
const fs=require('node:fs'),path=require('node:path'),v=require('../dist/verify.js');
const {literal,splitItems}=require('./resolve-source-scopes.cjs');
const ROOT=__dirname,fields=['model_raw','production_dates_raw','batch_raw'];
function labeled(raw){
 const s=String(raw||'').trim(),hits=[...s.matchAll(/(?:^|[\s；;])([^\s：:；;]+)[：:]/g)];
 if(hits.length<2||hits[0].index!==0)return null;
 const out=new Map();
 for(let i=0;i<hits.length;i++){const h=hits[i],key=h[1],value=s.slice(h.index+h[0].length,hits[i+1]?.index??s.length).replace(/[；;。]+$/,'').trim();if(out.has(key)||!value)return null;out.set(key,value)}
 return out;
}
function keyedGroups(r){
 const dates=labeled(r.production_dates_raw),batches=labeled(r.batch_raw);if(!dates||!batches||dates.size!==batches.size||[...dates.keys()].some(k=>!batches.has(k)))return null;
 let models=labeled(r.model_raw);
 if(!models){const items=splitItems(r.model_raw);models=new Map();for(const k of dates.keys()){const hits=items.filter(x=>x.startsWith(k));if(hits.length!==1)return null;models.set(k,hits[0])}if(items.length!==models.size)return null}
 if(models.size!==dates.size||[...dates.keys()].some(k=>!models.has(k)))return null;
 return [...dates].map(([k,d])=>({model:models.get(k),source_dates:d,batch_raw:batches.get(k),association_key:k}));
}
function apply(rows,inventory){
 for(const r of rows){
  if(r.domain==='汽车'||r.scope_rules)continue;
  const src=inventory[r.id],review=r.scope_review;
  if(src?.sha256!==r.sha256)throw Error('Reviewed scope inventory version mismatch '+r.id);
  const flags=[...(r.quality_flags||[]),r.scope_details?.status||'',r.scope_review?.note||''].join('；');
  if(/疑似|笔误|冲突|倒置|格式.*误|异常|未.*对应|未.*关联|未给出|需.*确认|未明确|型号缺失|未披露|不完整|排除|除外|不包括|但不含/.test(flags))continue;
  let groups=r.scope_details?.groups||[];
  let basis,assets=[];
  if(review?.source_sha256===r.sha256&&review.status==='范围条件AI辅助复核'&&groups.length){
   // Group evidence must be the reviewed named fields, with full coverage of each group.
   if(groups.some(g=>![g.model,g.source_dates,g.batch_raw].every(x=>typeof x==='string'&&x&&v.norm(review.evidence).includes(v.norm(x)))))continue;
   groups=keyedGroups(r)||groups;
   basis='既有范围条件AI辅助复核，按原组编译；本轮未重新视觉复核';
  }else{
   if(!fields.every(k=>r[k]&&r.field_review?.[k]?.evidence===r[k]&&/原图关键字段AI核对|原文关键字段AI核对/.test(r.field_review[k].status)))continue;
   // All three field transcriptions must cite the same locally verified official assets.
   const paths=fields.map(k=>r.field_review[k].sources||[]);
   const common=paths[0].filter(p=>paths.every(a=>a.includes(p)));
   assets=src.assets.filter(a=>a.local_file&&a.sha256&&common.includes(a.local_file));
   if(!assets.length)continue;
   groups=keyedGroups(r)||[{model:r.model_raw,source_dates:r.production_dates_raw,batch_raw:r.batch_raw}];
   basis='继承既有原图关键字段AI核对；三字段引用同一官方缓存图，已校验图片SHA256；本轮仅规则编译，未重新视觉复核';
  }
  const compiled=[];
  for(const g of groups){
   const model=g.model||'',date=g.source_dates||'',batch=g.batch_raw||'';
   // A combined multi-model field cannot become an arbitrary list of independent groups.
   const exactSpecification=/^\d+(?:\.\d+)?m[lL]\/只[、，,]\s*\d+只\/包$/.test(model)||/\d+(?:-\d+)?(?:V|W|Hz|mm|cm|mL|L)\b/i.test(model)&&!/[、；;]/.test(model)&&!/或|型号[:：]|规格[:：]|详|见/.test(model);
   let ms=v.models(model)||literal(model)||(exactSpecification?[model]:null);
   if(!ms||ms.length>1&&(!(v.batches(batch)?.length===1)||v.dateSpec(date)?.ranges.length!==1)||/原文第|可含子组|^[A-Z0-9-]+\/[A-Z][A-Z0-9-]+$/i.test(model)||/\d+#?[—~～-]\d+#?(?:码|$)/.test(model)&&r.category==='服饰鞋包')break;
   if(!v.dateSpec(date)||!(v.batches(batch)||v.batchRange(batch)))break;
   if((g.quantity_raw?.match(/型号/g)||[]).length>1)break;
   compiled.push({group_id:r.id+':reviewed'+(compiled.length+1),model,model_values:ms,source_dates:date,batch_raw:batch,required:{model:true,production:true,batch:true},evidence:`型号/规格：${model}；生产起止日期：${date}；生产批号/批次：${batch}`,locator:assets.length?assets.map(a=>a.local_file+' · 既有AI转录型号、生产期、批次三字段').join('；'):`${r.raw_file} · scope_review.evidence · 原条件组${compiled.length+1}`});
  }
  if(compiled.length!==groups.length||!compiled.length)continue;
  r.scope_rules={method:'source-reviewed-fields-v3',source_sha256:r.sha256,complete:true,groups:compiled,assets:assets.map(a=>({url:a.url,file:a.local_file,sha256:a.sha256})),note:basis,review_state:{rule_processing:'本轮逐组编译已有来源绑定字段，全部条件保持必填',ai_review:basis,human_review:'本轮未人工复核'}};
 }
 return rows;
}
if(require.main===module){const rows=JSON.parse(fs.readFileSync(0,'utf8'));process.stdout.write(JSON.stringify(apply(rows,JSON.parse(fs.readFileSync(path.join(ROOT,'scope-source-inventory.json'),'utf8')))))}
module.exports={apply,keyedGroups,labeled};
