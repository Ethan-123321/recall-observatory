const assert=require('node:assert/strict'),fs=require('node:fs');
const v=require('./dist/verify.js'),q=require('./dist/quality.js'),{enrich}=require('./dataset/enrich-scopes.cjs');
assert.equal(v.models('A1 A2'),null);
for(const s of ['165/66A S','JW-101 180mm','G-F-20（RHZKF6.8/30）','T1 明装','250g/包','260克/盒'])assert.deepEqual(v.models(s),[v.norm(s)]);
assert.equal(v.models('T1或T2'),null);assert.equal(v.batches('A1/A2'),null);
assert.equal(v.dateSpec('2024-08-07起至2024-08-09止').ranges[0][1],'2024-08-09');
assert.equal(v.dateSpec('2024-08-09起至2024-08-07止'),null);
const data=JSON.parse(fs.readFileSync('./dataset/recalls-2023-2025.json'));
let upgraded=0,carGroups=0;
for(const r of data.filter(r=>r.scope_rules?.method==='source-bound-normalization-v1')){
 assert.equal(r.scope_rules.source_sha256,r.sha256);
 for(const g of v.groups(r)){
  assert.ok(g.evidence);assert.ok(g.models);assert.ok(g.dateSpec);
  const input={model:g.models[0],production:g.dateSpec.ranges[0][0],batch:g.batchValues?.[0]||''};
  if(r.domain==='汽车'){
   assert.equal(v.check(r,input).state,'pending');assert.notEqual(q.audit(r,v).capability,q.capabilities[0]);
   assert.ok(v.check(r,input).groupResults.some(x=>x.state==='matched'));carGroups++;
  }else{
   assert.equal(v.check(r,input).state,'matched',r.id);assert.equal(v.check(r,{...input,model:'WRONG-UNIQUE-ID'}).state,'outside');
   if(g.required.batch)assert.equal(v.check(r,{...input,batch:''}).state,'pending');upgraded++;
  }
 }
}
const sample=data.find(r=>r.domain==='一般消费品'&&r.scope_review&&r.scope_rules?.method==='source-bound-normalization-v1');
const missing=structuredClone(sample);delete missing.scope_rules;missing.scope_details.groups[0].batch_raw='/';
assert.ok(!enrich(missing).scope_rules,'blank/slash batch cannot become all batches');
const ambiguous=structuredClone(sample);delete ambiguous.scope_rules;ambiguous.scope_review.note='型号对应关系未明确';
assert.ok(!enrich(ambiguous).scope_rules);
console.log(`PASS: ${upgraded} source-bound consumer/food groups; ${carGroups} car clauses remain VIN-pending; identifiers, missing batches and ambiguous mappings`);
