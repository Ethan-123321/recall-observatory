const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const core=require('./dist/research-core.js'),a=require('./dist/analysis.js'),v=require('./dist/verify.js');
const manifest=JSON.parse(fs.readFileSync('./research/tasks.json','utf8')),rows=JSON.parse(fs.readFileSync('./dataset/recalls-2023-2025.json','utf8'));
const defaults={domain:'全部',year:'全部',category:'全部',risk:'全部',query:'',scope:'全部',from:'',to:'',month:''};
for(let i=1;i<=4;i++){
 const tasks=core.schedule('P00'+i,manifest.tasks);assert.equal(tasks.length,8);assert.equal(new Set(tasks.map(t=>t.condition)).size,2);assert.equal(new Set(tasks.map(t=>t.variant)).size,2);
 for(const task of tasks){
  const filters={...defaults,...task.filters},view={filtered:a.filter(rows,filters),currentFilters:()=>filters};
  if(task.type==='filter'){assert.ok(task.expected_count>0);assert.equal(core.check(task,view,[]),true);assert.equal(core.check(task,{...view,filtered:[]},[]),false)}
  if(task.type==='peak'){assert.equal(core.check(task,view,[],task.expected_months.join(',')),true);assert.equal(core.check(task,view,[],'1900-01'),false)}
  if(task.type==='verify'){view.verifyResults=[v.check(rows.find(r=>r.id===task.notice_id),task.product)];assert.equal(core.check(task,view,[]),false);assert.equal(core.check(task,view,[{kind:'evidence',locator:task.notice_id+':g1'}]),true)}
  if(task.type==='recover'){const events=[{kind:'filters',filters},{kind:'filters',filters:{...filters,risk:task.intermediate_risk}},{kind:'filters',filters}];assert.equal(core.check(task,view,events),true);assert.equal(core.check(task,view,events.slice(0,2)),false)}
 }
}
assert.equal(core.schedule('Alice',manifest.tasks).length,0);
let clock=10000;const sandbox={ResearchStudy:core,recallResearch:manifest,crypto:require('node:crypto'),performance:{now:()=>clock},Date,clearInterval,localStorage:{setItem(){}}};vm.createContext(sandbox);vm.runInContext(fs.readFileSync('./dist/research.js','utf8')+';this.research=RecallResearch;',sandbox);
const task=core.schedule('P001',manifest.tasks)[0],filters={...defaults,...task.filters},view={researchActive:{task,participant:'P001',started:Date.now()-5000,started_perf:5000,started_at:new Date().toISOString(),events:[],observer_errors:0,help_count:0,validation_failures:0},researchRecords:[],researchWorkload:'',researchAnswer:'',currentFilters:()=>filters,filtered:a.filter(rows,filters)};
sandbox.research.methods.finishResearch.call(view,false);assert.equal(view.researchRecords.length,0);assert.equal(view.researchActive.completed_perf,10000);
clock=20000;view.researchWorkload=3;sandbox.research.methods.finishResearch.call(view,false);assert.equal(view.researchRecords[0].elapsed_ms,5000);assert.equal(view.researchActive,null);assert.equal(core.validateRecord(view.researchRecords[0]),true);
console.log('PASS: balanced materials, source-based goals, required evidence, recovery sequence and task timing excludes rating time');
