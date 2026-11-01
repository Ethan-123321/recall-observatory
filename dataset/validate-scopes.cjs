/* Reproducible local verification. Does not load credentials or call an external service. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),{spawnSync}=require('node:child_process');
const ROOT=path.dirname(__dirname),source=path.join(__dirname,'recalls-2023-2025.json');
const hash=()=>crypto.createHash('sha256').update(fs.readFileSync(source)).digest('hex'),version=hash();
const tests=['test_scope_resolution.cjs','test_quality.cjs','test_scope.cjs','test_verify.cjs','test_scope_enrichment.cjs','test_pending_resolution.cjs','test_visualization.cjs','test_navigation.cjs','test_scope_template.cjs','evaluate-scope.cjs'];
const results=[];
for(const file of tests){const r=spawnSync(process.execPath,[file],{cwd:ROOT,encoding:'utf8'});results.push({test:file,passed:r.status===0});console.log(file,r.status===0?'PASS':'FAIL');if(r.status!==0)console.error((r.stderr||r.stdout||r.error?.message||'No output').slice(-4000))}
const python=spawnSync('python',['-X','utf8','test_scope_stats.py'],{cwd:ROOT,encoding:'utf8',env:{...process.env,RECALL_SKIP_ENV:'1'}});results.push({test:'test_scope_stats.py (2 tests, including real loopback HTTP)',passed:python.status===0});console.log('test_scope_stats.py',python.status===0?'PASS':'FAIL');if(python.status!==0)console.error((python.stderr||python.error?.message||'No output').slice(-4000));
if(hash()!==version)throw Error('Formal data changed while verifying');
const report=JSON.parse(fs.readFileSync(path.join(__dirname,'scope-resolution-report.json'))),evaluation=JSON.parse(fs.readFileSync(path.join(__dirname,'evaluation/scope-results.json')));
const validation={date:'2026-11-01',source_sha256:version,status:results.every(x=>x.passed)?'通过':'未通过',suites:results,rule_cases:{total:evaluation.count,correct:evaluation.results.filter(x=>x.correct).length,false_matches:evaluation.false_matches,false_exclusions:evaluation.false_exclusions,overconfident:evaluation.overconfident},full_source_integrity_count:JSON.parse(fs.readFileSync(source)).length,target_ledger_count:report.target_count,browser_visual_check:{passed:false,reason:'内置浏览器无法访问本机端口；本机Computer Use因无法可靠识别浏览器URL而停止。已完成Vue模板编译和图表筛选逻辑测试，未宣称视觉验收。'},review_note:'继承已有AI转录的规则编译不代表本轮重新视觉复核；本轮人工复核未完成。旧评估的部分预期按更严格批号证据门槛改为待确认，旧版案例已完整保留。'};
validation.expected_case_revision_count=JSON.parse(fs.readFileSync(path.join(__dirname,'evaluation/scope-cases.json'))).expected_revisions.length;
fs.writeFileSync(path.join(__dirname,'scope-validation-20261101.json'),JSON.stringify(validation,null,2)+'\n');
require('./build-quality.cjs')();
if(!results.every(x=>x.passed))process.exitCode=1;
