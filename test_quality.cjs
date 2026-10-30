const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),crypto=require('node:crypto');
const q=require('./dist/quality.js'),v=require('./dist/verify.js');
const source=fs.readFileSync('./dataset/recalls-2023-2025.json'),notices=JSON.parse(source),rows=notices.map(r=>q.audit(r,v)),summary=q.summary(rows);
assert.equal(rows.length,1308);
for(const r of rows){
 assert.ok(q.capabilities.includes(r.capability));assert.ok(r.reasons.length);
 for(const f of Object.values(r.fields)){
  assert.ok(q.statuses.includes(f.status));assert.ok(f.reason);
  if(f.status==='可直接使用'){assert.ok(f.evidence);assert.equal(f.evidence.sha256,r.sha256);assert.ok(f.normalized_value)}
 }
 if(r.domain==='汽车')assert.notEqual(r.capability,q.capabilities[0]);
}
assert.equal(Object.values(summary.by_capability).reduce((a,b)=>a+b,0),rows.length);
for(const c of Object.values(summary.fields))assert.equal(Object.values(c).reduce((a,b)=>a+b,0),rows.length);
// Empty fields and ambiguous old missing-field labels cannot become non-disclosure.
const base={id:'test',domain:'一般消费品',year:'2025',source_url:'https://example.com/notice',sha256:'abc',model_raw:'A1',production_dates_raw:'2025-01-01至2025-03-01',scope_assessment:'按型号与生产日期界定',review_evidence:{model_raw:'A1',production_dates_raw:'2025-01-01至2025-03-01'}};
assert.equal(q.audit(base,v).fields.brand.status,'待审计');
assert.equal(q.audit({...base,field_review:{brand:{status:'原图未明确披露或无法可靠辨认，保留缺失'}}},v).fields.brand.status,'待审计');
assert.equal(q.audit({...base,brand:'测试品牌'},v).fields.brand.status,'原文有信息，尚未整理');
assert.equal(q.audit({...base,field_review:{model_raw:{evidence:'A1',source_sha256:'different'}}},v).fields.model_raw.status,'原文存在歧义或冲突');
assert.notEqual(q.audit({...base,scope_details:{groups:[{model:'原文第1组（可含子组）',source_dates:base.production_dates_raw}]}},v).capability,q.capabilities[0]);
assert.notEqual(q.audit({...base,quality_flags:['原文日期倒置']},v).capability,q.capabilities[0]);
assert.equal(q.summary([]).count,0);
for(const id of ['art_31401ac19ceb420d8b83e702e9a890cf','art_77006229eec14fe68504694b92eeb1da','art_f4fe421e182c4e42a7e9b0aba738c96d','art_280411cbe0554b1791251299bec3dc09'])assert.equal(rows.find(r=>r.id===id).capability,q.capabilities[0]);
// Exports must agree with the live browser's dataset and policy.
const ledger=JSON.parse(fs.readFileSync('./dataset/capability-ledger.json','utf8')),report=JSON.parse(fs.readFileSync('./dataset/audit-summary.json','utf8'));
assert.deepEqual(ledger,rows);assert.equal(report.source_sha256,crypto.createHash('sha256').update(source).digest('hex'));
assert.deepEqual(report.fields,summary.fields);assert.deepEqual(report.by_capability,summary.by_capability);
const context=vm.createContext({URL});vm.runInContext(fs.readFileSync('./dist/dataset-multidomain.js','utf8')+';globalThis.records=recallDataset;',context);
assert.equal(JSON.stringify(context.records),JSON.stringify(notices));
assert.equal(fs.readFileSync('./dataset/capability-ledger.csv','utf8'),q.csv(rows));
console.log('PASS: audit evidence, ambiguity, source versions, domain limits, all field totals and browser/export parity ('+rows.length+' notices)');
