const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const a=require('./dist/analysis.js'),q=require('./dist/quality.js'),v=require('./dist/verify.js');
const source=JSON.parse(fs.readFileSync('./dataset/recalls-2023-2025.json','utf8'));
const tagged=source.map(r=>({...r,capability:q.audit(r,v).capability}));
for(const rows of [tagged,tagged.filter(r=>r.domain==='食品'),tagged.filter(r=>r.category==='玩具'),[]]){
 const stack=a.capabilityStack(rows,q.capabilities);
 assert.equal(stack.totals.reduce((x,y)=>x+y,0),rows.length);
 stack.categories.forEach((category,i)=>assert.equal(stack.series.reduce((sum,s)=>sum+s.values[i],0),rows.filter(r=>r.category===category).length));
 for(const unit of ['year','month']){
  const chart=a.riskComposition(rows,unit);
  assert.equal(chart.samples.reduce((x,y)=>x+y,0),rows.length);
  chart.periods.forEach((period,i)=>{
   const group=rows.filter(r=>r.published_date.startsWith(period));
   assert.equal(chart.samples[i],group.length);
   assert.equal(chart.tagTotals[i],group.reduce((n,r)=>n+new Set(r.risk_tags).size,0));
   assert.equal(chart.series.reduce((n,s)=>n+s.counts[i],0),chart.tagTotals[i]);
   const percent=chart.series.reduce((n,s)=>n+s.proportions[i],0);
   assert.ok(Math.abs(percent-(chart.tagTotals[i]?100:0))<1e-8);
  });
 }
}
// Repeated tags on one notice never inflate a single risk count or its denominator.
const overlap=[{published_date:'2024-01-01',risk_tags:['触电','火灾','触电']},{published_date:'2024-01-02',risk_tags:['火灾']}];
const chart=a.riskComposition(overlap,'month',['2024-01','2024-02']);
assert.deepEqual(chart.samples,[2,0]);assert.deepEqual(chart.tagTotals,[3,0]);
assert.equal(chart.series.find(s=>s.name==='触电').counts[0],1);
assert.equal(chart.series.find(s=>s.name==='火灾').proportions[0],200/3);
assert.throws(()=>a.capabilityStack([{category:'玩具',capability:'未分类'}],q.capabilities));
// Exercise the actual navigation methods against the same filtering function as the UI.
const context={RecallQuality:q,nextTick:f=>f()};vm.createContext(context);
vm.runInContext(fs.readFileSync('./dist/analysis-advanced.js','utf8')+';this.mixin=RecallAdvancedAnalysis;',context);
const view={domain:'一般消费品',year:'全部',category:'全部',risk:'全部',scope:'全部',query:'',from:'2023-01-01',to:'2025-12-31',month:'',riskTimeUnit:'month',goSection(){}};
context.mixin.methods.openRiskSlice.call(view,'2025-07','触电');
const actual=a.filter(source,view);
assert.equal(view.domain,'一般消费品');assert.equal(view.page,2);
assert.ok(actual.every(r=>r.published_date.startsWith('2025-07')&&r.risk_tags.includes('触电')));
assert.equal(actual.length,source.filter(r=>r.domain==='一般消费品'&&r.published_date.startsWith('2025-07')&&r.risk_tags.includes('触电')).length);
context.mixin.methods.showCapabilityDetails.call(view,'玩具',q.capabilities[1]);
assert.equal(view.page,3);assert.equal(view.qualityCapability,q.capabilities[1]);assert.equal(view.category,'玩具');
console.log('PASS: category capability totals, multi-label composition denominators, zero periods, proportions and chart-to-list navigation');
