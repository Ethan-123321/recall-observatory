// Run after the main dataset build. Does not change published source records.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const q=require('../dist/quality.js'),v=require('../dist/verify.js');
function build(){
 const source=fs.readFileSync(path.join(__dirname,'recalls-2023-2025.json'));
 const notices=JSON.parse(source),rows=notices.map(r=>q.audit(r,v));
 if(new Set(rows.map(r=>r.id)).size!==rows.length)throw Error('公告ID重复，拒绝生成质量台账');
 const summary={...q.summary(rows),source_sha256:crypto.createHash('sha256').update(source).digest('hex'),generated_at:new Date().toISOString(),audit_status:'基于既有证据的自动预审，待审计与歧义项尚未完成全量原文复核'};
 const write=(name,data)=>fs.writeFileSync(path.join(__dirname,name),JSON.stringify(data,null,2)+'\n');
 write('capability-ledger.json',rows);write('audit-summary.json',summary);
 fs.writeFileSync(path.join(__dirname,'capability-ledger.csv'),q.csv(rows));
 const issues=rows.flatMap(r=>Object.entries(r.fields).filter(([,f])=>!['可直接使用','不适用'].includes(f.status)).map(([field,f])=>({id:r.id,field,status:f.status,reason:f.reason,source_url:r.source_url})));
 write('audit-issues.json',issues);
 const lines=['# 全量数据质量自动预审报告','',`数据：${rows.length}份公告；源文件SHA256：${summary.source_sha256}。`,`规则：${q.version}；生成时间：${summary.generated_at}。`,'','本报告为既有复核证据的自动预审，不表示已重新逐条查阅全部原文。空字段或历史含糊标签不自动归为公告未披露；待审计项必须继续复核。','',...q.capabilities.map(c=>`- ${c}：${summary.by_capability[c]||0}份`),'','## 字段状态','', '| 字段 | '+q.statuses.join(' | ')+' |','| --- | '+q.statuses.map(()=> '---:').join(' | ')+' |',...Object.entries(q.fields).map(([k,label])=>'| '+label+' | '+q.statuses.map(s=>summary.fields[k][s]).join(' | ')+' |'),'','核验能力基于当前引擎、条件组范围与字段证据保守评定；不是产品命中结果。汽车仅初筛。字段可用不保证跨字段关联已核对。','',`问题字段记录：${issues.length}条；允许同公告多项。明细见 capability-ledger.json/csv 与 audit-issues.json。`];
 fs.writeFileSync(path.join(__dirname,'AUDIT_REPORT.md'),lines.join('\n')+'\n');
 console.log(JSON.stringify({count:rows.length,capabilities:summary.by_capability,issues:issues.length}));
 return {rows,summary};
}
if(require.main===module)build();
module.exports=build;
