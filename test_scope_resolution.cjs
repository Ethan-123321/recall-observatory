const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),crypto=require('node:crypto'),path=require('node:path');
const v=require('./dist/verify.js'),q=require('./dist/quality.js');
const data=JSON.parse(fs.readFileSync('dataset/recalls-2023-2025.json')),base=require('./dataset/capability-baseline-20261101.json'),report=require('./dataset/scope-resolution-report.json'),issues=require('./dataset/scope-blocker-ledger.json'),inventory=require('./dataset/scope-source-inventory.json');
const byId=id=>{const r=data.find(x=>x.id===id);assert.ok(r,id);return r};
const verify=(id,input,state)=>{const result=v.check(byId(id),input);assert.equal(result.state,state,JSON.stringify({id,input,codes:result.reasonCodes}));return result};
// Visually checked real image: the second model's production day and batch must never match the first.
const bike='art_a9c7b008228d4865888d0be82d4f68c2';
verify(bike,{model:'TDT006Z',production:'2020-10-28',batch:'20201028'},'matched');
verify(bike,{model:'TDT006Z',production:'2020-09-18',batch:'20200918'},'outside');
verify(bike,{model:'TDT006Z',production:'2020-10-28',batch:'20200918'},'outside');
const missing=verify(bike,{model:'TDT006Z',production:'2020-10-28'},'pending');
assert.deepEqual(missing.guidance.userMissing,['批号 / 序列号']);assert.equal(missing.guidance.sourceGaps.length,0);
const lamp='art_7bae113a23a740ec894b51638d3d2f51';
for(const production of ['2020-06-05','2021-12-26'])verify(lamp,{model:'YY-GD-35W-5500K',production,batch:'JDSCRK00000066'},'matched');
verify(lamp,{model:'YY-GD-35W-5500K',production:'2020-06-04',batch:'JDSCRK00000066'},'outside');
verify(lamp,{model:'YY-GD-35W-5500K',production:'2020-06',batch:'JDSCRK00000066'},'pending');
verify(lamp,{model:'YY-GD-35W-5500K',production:'2021-12-27',batch:'JDSCRK00000066'},'outside');
verify(lamp,{model:'YY-GD-35W-5500K',production:'2021-07-01',batch:'JDSCRK00000020'},'outside');
// Named parentheticals, not list position, bind the full specification to its batch.
const paper='art_eeb40f40b11044639ecd4cd703674e0f';
verify(paper,{model:'24K田字薄(187mm*142mm)',production:'2024-06-05',batch:'2024/6/5'},'matched');
verify(paper,{model:'24K田字薄(187mm*142mm)',production:'2024-06-05',batch:'2025/3/3'},'outside');
// Named clauses are joined by product identity, including when their order differs.
const seal='art_2bc8b6063269474b99c59ec572f22da8';
verify(seal,{model:'300mL/支 厨卫透明',production:'2022-01-09',batch:'20220109'},'matched');
verify(seal,{model:'300mL/支 厨卫透明',production:'2021-09-11',batch:'20210911'},'outside');
verify(seal,{model:'300mL/支 厨卫透明',production:'2022-01-09',batch:'20210911'},'outside');
const parsed=require('./dataset/resolve-reviewed-scopes.cjs').keyedGroups({...byId(seal),batch_raw:'长效防霉密封胶：20210911；防霉密封胶（0级防霉）：20220109'});
assert.equal(parsed.find(g=>g.association_key==='防霉密封胶（0级防霉）').batch_raw,'20220109');
// Explicit month precision and discrete slash-list batch codes are executable without filling gaps.
verify('art_794b1de9efdc47d7af2dc6ab7a92c138',{model:'25只/袋',production:'2020-04',batch:'20200426'},'matched');
verify('art_877dd9efc32043e3a5de6f90eaf0c93c',{model:'折叠型',production:'2022-08-07',batch:'20220807'},'outside');
const serial='art_620b5d3a3282408c91fb1aca94f4e5dd';
for(const batch of ['20250823','20250830'])verify(serial,{model:'210mL',production:'2025-08-25',batch},'matched');
for(const batch of ['20250822','20250831','202508230'])verify(serial,{model:'210mL',production:'2025-08-25',batch},'outside');
assert.deepEqual(v.batchRange('XSL250308-XSL251026'),{prefix:'XSL',start:'250308',end:'251026',width:6,raw:'XSL250308-XSL251026'});
assert.equal(v.batchRange('XSL250308-251026'),null,'never expand an omitted prefix');
assert.equal(v.batchRange('40330001-0523'),null,'never expand abbreviated endpoints');
assert.equal(v.batchRange('20250904-20250927/--'),null,'a placeholder cannot be dropped from a range');
const towel='art_f1e340542d8d4a689fe00e2e4f1563da';
for(const batch of ['XSL250308','XSL251026'])verify(towel,{model:'30*40 切边',production:'2025-03-08',batch},'matched');
for(const batch of ['XSL250307','XSL251027','250308','XSL0250308','OTHER250308'])verify(towel,{model:'30*40 切边',production:'2025-03-08',batch},'outside');
// Date-based batch ranges keep their own date, independently of production date.
const datedBatch='art_633c64b971274a2f9bacdf2fd4274c22';
verify(datedBatch,{model:'18.5*8.5',production:'2024-08-02',batch:'2024-08-01'},'matched');
verify(datedBatch,{model:'18.5*8.5',production:'2024-08-02',batch:'2024-08-15'},'matched');
verify(datedBatch,{model:'18.5*8.5',production:'2024-08-02',batch:'2024-08-16'},'outside');
assert.ok(verify(datedBatch,{model:'18.5*8.5',production:'2024-08-02',batch:'2024-08'},'pending').reasonCodes.includes('batch_precision'));
assert.equal(v.dateSpec('2022年9月10日至2022年9年11日'),null,'do not silently repair an incorrect 年 character');
// Missing/placeholder batch is an evidence gap even after the user fills an invented batch.
const noBatch='art_2eaa74cf65a04792a51d89af9d34ed5d';
const sourceGap=verify(noBatch,{model:'Z0207D',production:'2025-05-16',batch:'ANY'},'pending');
assert.ok(sourceGap.guidance.sourceGaps.includes('批号 / 序列号'));assert.equal(sourceGap.guidance.userMissing.length,0);
assert.notEqual(q.audit(byId(noBatch),v).capability,q.capabilities[0]);
const car='art_9cc07a2ee0b2419f882d76dbb8e87001';
const carResult=verify(car,{model:'部分进口i7系汽车',production:'2022-12-12'},'pending');
assert.equal(carResult.guidance.carPreMatch,true);assert.ok(carResult.reasonCodes.includes('vin'));
const carCross=verify(car,{model:'部分进口i7系汽车',production:'2025-05-17'},'pending');
assert.equal(carCross.guidance.carPreMatch,false);
// Every targeted notice has a concrete record; every new complete decision has executable source evidence.
assert.equal(issues.length,base.records.filter(r=>r.capability!==q.capabilities[0]).length);
assert.equal(new Set(issues.map(r=>r.id)).size,issues.length);
for(const r of data){
 assert.equal(r.scope_issue.current,q.audit(r,v).capability,r.id);
 assert.equal(inventory[r.id].sha256,r.sha256);
 assert.equal(crypto.createHash('sha256').update(fs.readFileSync('dataset/'+r.raw_file)).digest('hex'),r.sha256);
 for(const e of r.scope_issue.evidence){assert.ok(e.locator);assert.equal(e.source_sha256,r.sha256)}
 for(const asset of r.scope_rules?.assets||[]){const file=path.resolve('dataset',asset.file);assert.ok(file.startsWith(path.resolve('dataset')+path.sep));assert.equal(crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'),asset.sha256);assert.ok(inventory[r.id].assets.some(a=>a.sha256===asset.sha256&&a.url===asset.url))}
 assert.match(r.scope_issue.processing.human_review,/未人工复核/);
 if(r.scope_issue.before!==q.capabilities[0]&&q.audit(r,v).capability===q.capabilities[0]){
  const info=v.scopeInfo(r);assert.ok(info.complete&&info.executable);
  for(const g of info.groups){assert.ok(g.evidence||r.review_evidence?.model_raw||r.field_review?.model_raw?.evidence);const input={model:g.models[0],production:g.dateSpec.ranges[0][0],batch:g.batchValues?.[0]||(g.batchInterval?.kind==='date'?g.batchInterval.spec.ranges[0][0]:g.batchInterval?g.batchInterval.prefix+g.batchInterval.start:'')};for(const model of g.models)assert.equal(v.check(r,{...input,model}).state,'matched',r.id);assert.equal(v.check(r,{...input,model:'WRONG-UNIQUE-MODEL'}).state,'outside',r.id);if(g.required.batch){assert.equal(v.check(r,{...input,batch:''}).state,'pending',r.id);assert.equal(v.check(r,{...input,batch:'WRONG-UNIQUE-BATCH'}).state,g.batchInterval?.kind==='date'?'pending':'outside',r.id)}}
 }
 if(r.domain==='汽车')assert.notEqual(q.audit(r,v).capability,q.capabilities[0]);
}
assert.deepEqual(report.after,q.summary(data.map(r=>q.audit(r,v))).by_capability);
assert.equal(report.source_sha256,crypto.createHash('sha256').update(fs.readFileSync('dataset/recalls-2023-2025.json')).digest('hex'));
// The actual UI computed filters are used by chart clicks and equivalent dropdowns.
const ctx=vm.createContext({RecallQuality:q,RecallVerify:v,URL,console});vm.runInContext(fs.readFileSync('dist/quality-view.js','utf8')+';this.mixin=RecallQualityView',ctx);
const view={...ctx.mixin.data(),dataset:data};
view.qualityBase=ctx.mixin.computed.qualityLedger.call(view);
view.qualityCapability=q.capabilities[2];view.qualityCompareStage='before';assert.equal(ctx.mixin.computed.qualityRows.call(view).length,report.before[q.capabilities[2]]);
view.qualityCompareStage='after';assert.equal(ctx.mixin.computed.qualityRows.call(view).length,report.after[q.capabilities[2]]);
view.qualityCapability='';view.qualityBlocker='需要官方VIN确认';assert.equal(ctx.mixin.computed.qualityRows.call(view).length,data.filter(r=>r.domain==='汽车').length);
console.log('PASS: real source cross-group/date/batch/VIN regressions; every baseline target, every newly complete group, all source hashes, report parity and chart-to-list filters');
