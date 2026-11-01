const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const q=require('../dist/quality.js'),v=require('../dist/verify.js'),ROOT=__dirname;
const baseline=JSON.parse(fs.readFileSync(path.join(ROOT,'capability-baseline-20261101.json'),'utf8'));
const before=new Map(baseline.records.map(r=>[r.id,r]));
const names={body_extraction:'已有条件文字尚未提取或建模',assets:'候选图片或附件还需定位核对',mapping:'多型号、日期、批次对应关系尚未整理',field_identifier_gap:'已整理范围字段缺少可识别条件',not_disclosed:'既有复核明确记录公告未披露',source_uncertain:'公告证据完整性尚未证实',conflict:'原文疑点或冲突',official_confirmation:'需要生产者进一步确认',vin:'需要官方VIN确认'};
function annotate(rows,inventory){
 for(const r of rows){
  const audit=q.audit(r,v),info=v.scopeInfo(r),src=inventory[r.id],old=before.get(r.id);
  if(!old)throw Error('Baseline does not cover '+r.id);
  const missing=Object.entries(audit.fields).filter(([k,f])=>['model_raw','production_dates_raw','batch_raw'].includes(k)&&!['可直接使用','不适用'].includes(f.status)).map(([k,f])=>({field:k,label:f.label,status:f.status,raw:f.raw_value,reason:f.reason}));
  const blockers=[];const add=(code,detail,action)=>{if(!blockers.some(x=>x.code===code))blockers.push({code,label:names[code],detail,action})};
  const rangeNote=[r.scope_details?.status,r.scope_review?.note,...(r.quality_flags||[])].filter(Boolean).join('；');
  if(audit.capability!==q.capabilities[0]){
   if(r.domain==='汽车')add('vin','车型生产期初筛不能识别具体VIN是否列入召回。','准备17位VIN，通过公告生产者或召回中心官方查询核实。');
   if(info.conflicts.length)add('conflict',info.conflicts.join('；'),'保留原文，不擅自修正日期或批号；向公告生产者核实。');
   if(!info.complete&&(info.groups.some(g=>g.unresolved)||/未.*对应|未.*关联|不按顺序|未给出.*型号/.test(rangeNote)||((v.models(r.model_raw)?.length||0)>1&&(v.batches(r.batch_raw)?.length||0)>1)))add('mapping',rangeNote||'条件组尚未证明完整','按原文明确的产品名、型号或组号关联；禁止按顺序猜配。');
   const unsupported=info.groups.flatMap(g=>[['model',g.required.model,g.models,g.modelRaw],['production',g.required.production,g.dateSpec,g.dateRaw],['batch',g.required.batch,g.batchValues||g.batchInterval,g.batchRaw]].filter(x=>x[1]&&!x[2]));
   const placeholder=x=>!x||/^[-/\s]+$/.test(x)||/^(?:第)?[一二三四五六七八九十\d]+(?:个)?批(?:次)?$|^无$/.test(x);
   const written=unsupported.filter(x=>!placeholder(x[3]));
   if(written.length)add('body_extraction',written.map(x=>x[0]+'：'+x[3]).join('；'),'解析有证据的完整字段；区间、占位符和数量词不得当作单个标识。');
   if(unsupported.some(x=>placeholder(x[3])))add('field_identifier_gap',unsupported.filter(x=>placeholder(x[3])).map(x=>x[0]+'原字段：'+(x[3]||'空白')).join('；'),'用户补填不能弥补公告侧条件；继续核对完整原文或向生产者索取可识别的范围。这里只判定已整理字段，不断言全文未披露。');
   if(missing.some(x=>x.status==='公告未披露')||/型号.*未披露|批次.*未披露|没有.*批号|未给出.*批号/.test(rangeNote))add('not_disclosed',rangeNote||missing.filter(x=>x.status==='公告未披露').map(x=>x.label).join('；'),'此为既有AI辅助复核记录；若需个体确认请联系召回生产者，不能由用户输入补足公告证据。');
   const conditionAssets=src.assets.filter(a=>a.kind==='attachment'||a.local_file||/cms_files|W\d{10,}|\.\/.*\.(png|jpe?g)/i.test(a.target));
   if(written.length&&conditionAssets.length)add('assets',`存在${conditionAssets.length}个候选图片/附件，不能据此宣称其中必有缺失条件。`,'检查候选资产及已缓存图片；未解析资产保留待核验，不标记为本轮已视觉复核。');
   if(r.domain!=='汽车'&&(/SN|通过.*查询|首批|批次不完整|需.*厂家.*确认|需.*生产者.*确认/.test([r.batch_raw,rangeNote.replace(/不是厂家确认|非厂家确认/g,'')].join(' '))||blockers.some(b=>b.code==='field_identifier_gap')))add('official_confirmation',`批次原文：${r.batch_raw||'空白'}；${rangeNote}`,'使用公告列出的联系方式或官方序列号查询；不将缺失批号视为全批次。');
   if(!blockers.length)add('source_uncertain',rangeNote||audit.reasons.join('；'),'核对完整范围正文及资产，取得明确范围证据后再决定是否升级。');
  }
  const evidence=info.groups.map(g=>({group_id:g.id,model:g.modelRaw,production:g.dateRaw,batch:g.batchRaw,excerpt:g.evidence||r.scope_review?.evidence||'',locator:g.locator||r.scope_rules?.groups?.find(x=>x.group_id===g.id)?.locator||`${r.raw_file} · 既有范围摘录（未精确定位）`,source_url:r.source_url,source_sha256:r.sha256}));
  r.scope_issue={id:r.id,official_source:r.source_url,before:old.capability,current:audit.capability,targeted:old.capability!==q.capabilities[0],missing_fields:audit.capability===q.capabilities[0]?[]:missing,blockers,evidence,assets:src.assets.filter(a=>a.kind==='attachment'||a.local_file),required_user_inputs:[...new Set(info.groups.flatMap(g=>Object.entries(g.required).filter(([,on])=>on).map(([key])=>key)))],user_input_status:'仅表示运行核验时所需字段；未取得用户实物信息，不将其记为公告数据缺失。',result:old.capability!==audit.capability?'能力变化，见前后分类及条件证据':r.scope_rules?.method&&['source-table-exact-v2','source-image-reviewed-v2','source-reviewed-fields-v3'].includes(r.scope_rules.method)?'已补充可执行条件组，能力分类未变':'已逐条自动诊断；剩余条件尚未全部解决',processing:r.scope_rules?.review_state||{rule_processing:'本轮逐条自动诊断',ai_review:r.scope_review?.status||'沿用既有记录，未完成本轮逐条语义复核',human_review:'本轮未人工复核'},official_contact:r.contact_raw||null,external_attempt:r.id==='art_a2dbc3edb5bc4e51bd02b7c0dbe84832'?'2026-11-01尝试访问对应官方公告，网页工具返回不可访问；本地型号栏为请详附件，继续保留待确认。':null};
 }
 return rows;
}
function build(rows){
 const issues=rows.filter(r=>r.scope_issue.targeted).map(r=>r.scope_issue),counts={};
 for(const r of rows)for(const b of r.scope_issue.blockers)counts[b.label]=(counts[b.label]||0)+1;
 const changes=rows.filter(r=>r.scope_issue.before!==r.scope_issue.current).map(r=>({id:r.id,before:r.scope_issue.before,after:r.scope_issue.current,source_url:r.source_url,evidence:r.scope_issue.evidence,remaining_blockers:r.scope_issue.blockers,review_state:r.scope_issue.processing}));
 const report={date:'2026-11-01',baseline_source_sha256:baseline.source_sha256,source_sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(ROOT,'recalls-2023-2025.json'))).digest('hex'),before:baseline.summary.by_capability,after:q.summary(rows.map(r=>q.audit(r,v))).by_capability,target_count:issues.length,processed_count:issues.length,processing_scope:'逐条自动诊断全部目标；两份本地原图范围AI视觉核对，其余规则处理不称人工复核。',remaining_blockers:counts,changes,rule_version:v.version,unresolved:rows.filter(r=>r.scope_issue.blockers.length).map(r=>r.id)};
 const write=(n,x)=>fs.writeFileSync(path.join(ROOT,n),JSON.stringify(x,null,2)+'\n');
 report.by_domain=Object.fromEntries([...new Set(rows.map(r=>r.domain))].map(domain=>[domain,q.summary(rows.filter(r=>r.domain===domain).map(r=>q.audit(r,v))).by_capability]));
 report.transition_counts={};for(const c of changes){const key=c.before+' → '+c.after;report.transition_counts[key]=(report.transition_counts[key]||0)+1}
 report.upgraded_ids=changes.filter(c=>q.capabilities.indexOf(c.after)<q.capabilities.indexOf(c.before)).map(c=>c.id);
 report.downgraded_ids=changes.filter(c=>q.capabilities.indexOf(c.after)>q.capabilities.indexOf(c.before)).map(c=>c.id);
 report.mechanisms=Object.fromEntries([...new Set(rows.map(r=>r.scope_rules?.method).filter(Boolean))].map(method=>[method,rows.filter(r=>r.scope_rules?.method===method).length]));
 const validationPath=path.join(ROOT,'scope-validation-20261101.json');
 report.validation=fs.existsSync(validationPath)?JSON.parse(fs.readFileSync(validationPath,'utf8')):{status:'本轮验证结果尚未写入'};
 if(report.validation.source_sha256&&report.validation.source_sha256!==report.source_sha256)report.validation={status:'数据版本已变化，须重新执行验证'};
 write('scope-blocker-ledger.json',issues);write('scope-resolution-report.json',report);
 const quote=x=>'"'+String(x??'').replace(/"/g,'""')+'"';
 fs.writeFileSync(path.join(ROOT,'scope-blocker-ledger.csv'),'\ufeff'+[['公告ID','官方来源','处理前能力','当前能力','缺失字段','阻碍原因及补充方式','已有证据与位置','处理结果','复核实际状态'],...issues.map(i=>[i.id,i.official_source,i.before,i.current,JSON.stringify(i.missing_fields),JSON.stringify(i.blockers),JSON.stringify(i.evidence),i.result,JSON.stringify(i.processing)])].map(row=>row.map(quote).join(',')).join('\r\n'));
 const lines=['# 真实公告条件核验改进报告','',`处理日期：${report.date}；规则：${v.version}；原始目标${issues.length}份均有逐条诊断记录。`,'','处理范围是全量本地证据诊断与可执行规则补充，不表示全部公告已完成语义或图像复核。两份图像已在本轮由AI视觉核对，人工复核为未完成。','', '| 能力 | 处理前 | 处理后 |','|---|---:|---:|',...q.capabilities.map(c=>`| ${c} | ${report.before[c]||0} | ${report.after[c]||0} |`),'','## 剩余阻碍（可重叠）','',...Object.entries(counts).map(([k,n])=>`- ${k}：${n}份`),'','## 每份能力变化的公告及证据','',...changes.map(c=>`- ${c.id}：${c.before} → ${c.after}；[官方来源](${c.source_url})；${c.evidence.map(e=>e.excerpt+'〔'+e.locator+'〕').join('；')}`),'','## 尚未解决的事项','', '- 全量剩余公告逐项阻碍、已有证据、候选本地资产及补充方式见 scope-blocker-ledger.json/csv；不是以空字段断言官方未披露。','- 图片、附件和开放日期区间仍有未解析项；本轮未批量重新下载或视觉复核全部资产。','- 多型号条件未明确对应、占位批号、批次数量及原文冲突继续待确认，不能降低门槛升级。','- 型号“请详附件”的轮组公告本轮访问官方网页失败，仍需取得官方清单。','- 汽车全部保留VIN确认，提取条款不宣称完整；未匹配不代表产品安全。','- 日期批号按标签原文值匹配，不自动用生产日期替代批号。','',`基线SHA256：${baseline.source_sha256}；正式数据SHA256：${report.source_sha256}。`];
 lines.push('','## 按领域的最终能力','',...Object.entries(report.by_domain).map(([d,c])=>`${d}：${q.capabilities.map(k=>k+' '+(c[k]||0)+'份').join('；')}。`),'','## 实际能力变化','',...Object.entries(report.transition_counts).map(([k,n])=>`- ${k}：${n}份`),'','## 新增规则与证据约束','', '- 将本地HTML三字段单元格、已有来源绑定的AI范围转录和已校验SHA256的图片字段编译为执行规则；复用既有转录不标记为本轮重新视觉复核。','- 按产品名或型号键关联分组，不按列表序号拼接；同一字段列出的多个型号只有在共享唯一日期区间及唯一批号时才建立同一条件组。','- 处理明确的离散日期、年月精度、同年省略日期、完整紧凑日期、日期型批号区间、明确的数字序列区间、批号标签及批次数量后缀。保留范围原文，不修正疑似错字。','- 批号为空、斜杠或只有批次数量时不免核批号；车型与日期结果始终不能代替VIN确认。','', '## 验证结果及限制','', '```json',JSON.stringify(report.validation,null,2),'```');
 fs.writeFileSync(path.join(ROOT,'SCOPE_RESOLUTION_20261101.md'),lines.join('\n')+'\n');return report;
}
module.exports={annotate,build,names};
if(require.main===module)process.stdout.write(JSON.stringify(annotate(JSON.parse(fs.readFileSync(0,'utf8')),JSON.parse(fs.readFileSync(path.join(ROOT,'scope-source-inventory.json'),'utf8')))));
