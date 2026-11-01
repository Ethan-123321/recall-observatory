const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const v=require('./dist/verify.js');
const root=path.join(__dirname,'dataset/evaluation');
const fixture=fs.readFileSync(path.join(root,'scope-cases.json')),suite=JSON.parse(fixture);
const states=['matched','outside','pending'],labels={matched:'符合',outside:'不符合',pending:'待确认'};
const matrix=Object.fromEntries(states.map(s=>[s,Object.fromEntries(states.map(t=>[t,0]))]));
const actual=suite.cases.map(c=>{
 const r=v.check(c.notice,c.input);matrix[c.expected][r.state]++;
 for(const g of r.groupResults)for(const row of g.rows){assert.equal(row.group_id,g.id);assert.ok(row.evidence.locator);}
 if(r.state==='pending')assert.ok(r.nextSteps.length,'待确认必须给出具体行动：'+c.case_id);
 return {case_id:c.case_id,scenario:c.scenario,origin:c.origin,notice_id:c.notice.id,source_url:c.notice.source_url||null,source_sha256:c.notice.sha256||null,input:c.input,expected:c.expected,actual:r.state,correct:c.expected===r.state,basis:c.basis,reason_codes:r.reasonCodes,decisive_groups:r.decisiveGroupIds};
});
const definite=actual.filter(c=>c.actual!=='pending'),correct=actual.filter(c=>c.correct),count=actual.length;
const countBy=(rows,key)=>Object.fromEntries([...new Set(rows.map(key))].map(k=>[k,rows.filter(r=>key(r)===k).length]));
const report={suite_version:suite.version,rule_version:v.version,fixture_sha256:crypto.createHash('sha256').update(fixture).digest('hex'),data_sha256:suite.data_sha256,count,accuracy:correct.length/count,deterministic_coverage:definite.length/count,deterministic_accuracy:definite.length?definite.filter(c=>c.correct).length/definite.length:null,false_matches:actual.filter(c=>c.actual==='matched'&&c.expected==='outside').length,false_exclusions:actual.filter(c=>c.actual==='outside'&&c.expected==='matched').length,overconfident:actual.filter(c=>c.expected==='pending'&&c.actual!=='pending').length,matrix,pending_reasons:countBy(actual.filter(c=>c.actual==='pending').flatMap(c=>c.reason_codes.map(code=>({code}))),c=>c.code),by_scenario:countBy(actual,c=>c.scenario),by_origin:countBy(actual,c=>c.origin),unique_source_notices:new Set(actual.filter(c=>c.source_url).map(c=>c.notice_id)).size,results:actual};
fs.writeFileSync(path.join(root,'scope-results.json'),JSON.stringify(report,null,2)+'\n');
const pct=x=>x==null?'不适用':(x*100).toFixed(1)+'%';
const text=['# 复杂范围核验评估报告','',`日期：2026-11-01；规则：${v.version}；案例集：${suite.version}。`,`案例：${count}；公告来源关联输入${report.by_origin['公告来源关联案例']}例，来自${report.unique_source_notices}份公告；规则规格案例${report.by_origin['规则规格案例']}例。案例作者与版本记录于案例文件。`,'',`本轮预期修订${suite.expected_revisions?.length||0}例：批号缺失不再默认免除；旧案例完整保留在scope-cases-v4-preserved.json。`, '', '本报告验证明确的规则与边界，不以此推算全部公告上的产品命中准确率。未使用真人实验数据。','',`- 三分类准确率：${pct(report.accuracy)}`,`- 确定性判断覆盖率：${pct(report.deterministic_coverage)}`,`- 确定性判断准确率：${pct(report.deterministic_accuracy)}`,`- 错误匹配：${report.false_matches}；错误排除：${report.false_exclusions}；将待确认错误确定化：${report.overconfident}`,'','## 混淆矩阵','', '| 预期 / 实际 | 符合 | 不符合 | 待确认 |','| --- | ---: | ---: | ---: |',...states.map(s=>'| '+labels[s]+' | '+states.map(t=>matrix[s][t]).join(' | ')+' |'),'','## 待确认原因（可重叠）','',...Object.entries(report.pending_reasons).map(([code,n])=>`- ${code}：${n}`),'','## 使用范围','', '覆盖多组关系、同型号不同日期、跨组拼接、离散日期、月份精度、批号缺失、简称、范围未完整枚举、原文冲突、排除条件、汽车VIN及食品规格缺失。详细输入、预期依据与实际结果见scope-cases.json及scope-results.json。','',`案例文件SHA256：${report.fixture_sha256}。`,`正式数据源SHA256：${suite.data_sha256}。`];
fs.writeFileSync(path.join(root,'SCOPE_EVALUATION.md'),text.join('\n')+'\n');
console.log(JSON.stringify({count,correct:correct.length,coverage:report.deterministic_coverage,errors:count-correct.length}));
for(const c of actual.filter(c=>!c.correct))console.error(c.case_id,c.scenario,'expected',c.expected,'actual',c.actual);
if(correct.length!==count)process.exitCode=1;
