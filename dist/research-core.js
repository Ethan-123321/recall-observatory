const ResearchStudy=(()=>{
 const order=[['manual','A','voice_chart','B'],['voice_chart','A','manual','B'],['manual','B','voice_chart','A'],['voice_chart','B','manual','A']];
 function schedule(participant,tasks){const n=Number(String(participant).replace(/^P/,''));if(!/^P\d{3,5}$/.test(participant)||!n)return [];const sequence=order[(n-1)%4];return [0,1].flatMap(block=>tasks.filter(t=>t.variant===sequence[block*2+1]).map(t=>({...t,condition:sequence[block*2],block:block+1,key:(block+1)+'-'+t.id})));}
 const equalIds=(a,b)=>a.length===b.length&&[...a].sort().every((id,i)=>id===[...b].sort()[i]);
 function check(task,view,events,answer=''){
  const filters=view.currentFilters(),matches=Object.entries(task.filters||{}).every(([k,v])=>filters[k]===v);
  if(task.type==='filter')return matches&&equalIds(view.filtered.map(r=>r.id),task.expected_ids);
  if(task.type==='peak'){const months=[...new Set(answer.match(/20\d{2}-\d{2}/g)||[])];return matches&&view.filtered.length===task.sample_count&&equalIds(months,task.expected_months);}
  if(task.type==='verify')return !!view.verifyResults?.some(r=>r.notice.id===task.notice_id&&r.state===task.expected_state)&&events.some(e=>e.kind==='evidence'&&e.locator.startsWith(task.notice_id+':'));
  if(task.type==='recover'){
   const states=events.filter(e=>e.kind==='filters').map(e=>e.filters),first=states.findIndex(f=>Object.entries(task.filters).every(([k,v])=>f[k]===v));
   const changed=states.findIndex((f,i)=>i>first&&first>=0&&f.year===task.filters.year&&f.category===task.filters.category&&f.risk===task.intermediate_risk);
   return matches&&changed>=0&&states.slice(changed+1).some(f=>Object.entries(task.filters).every(([k,v])=>f[k]===v));
  }
  return false;
 }
 function validateRecord(r){return r&&typeof r==='object'&&typeof r.trial_id==='string'&&/^P\d{3,5}$/.test(r.participant)&&['manual','voice_chart'].includes(r.condition)&&['filter','peak','verify','recover'].includes(r.task_type)&&typeof r.success==='boolean'&&Number.isFinite(r.elapsed_ms)&&r.elapsed_ms>=0&&r.elapsed_ms<=86400000&&/^[a-f0-9]{64}$/.test(r.data_version)&&Number.isFinite(Date.parse(r.started_at))&&r.study_id==='recall-interaction-v1';}
 return {schedule,check,validateRecord};
})();
if(typeof module!=='undefined')module.exports=ResearchStudy;
