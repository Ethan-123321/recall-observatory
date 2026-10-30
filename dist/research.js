const RecallResearch={
 data:()=>({researchParticipant:'P001',researchRecords:[],researchActive:null,researchAnswer:'',researchWorkload:'',researchMessage:'',researchClock:0,researchTimer:null}),
 computed:{
  researchSchedule(){return ResearchStudy.schedule(this.researchParticipant,recallResearch.tasks)},
  researchCurrentRecords(){return this.researchRecords.filter(r=>r.participant===this.researchParticipant)},
  researchElapsed(){return this.researchActive?Math.max(0,Math.round(((this.researchActive.completed_ms||this.researchClock)-this.researchActive.started)/1000)):0},
  researchManualActive(){return this.researchActive?.task.condition==='manual'},
  researchParticipants(){return new Set(this.researchRecords.map(r=>r.participant)).size}
 },
 watch:{filtered(){if(this.researchActive)this.studyEvent('filters',{filters:this.currentFilters()})}},
 methods:{
  researchDone(task){return this.researchCurrentRecords.some(r=>r.schedule_key===task.key)},
  studyEvent(kind,extra={}){if(!this.researchActive)return;this.researchActive.events.push({kind,at_ms:Math.max(0,Math.round(performance.now()-this.researchActive.started_perf)),...extra})},
  recordStudyEvidence(locator){this.studyEvent('evidence',{locator})},
  markTranscriptEdit(){if(this.lastTranscribedText&&this.lastTranscribedText!==this.assistantText){this.studyEvent('transcript_edit');this.lastTranscribedText=this.assistantText}},
  startResearch(task){
   if(this.researchActive||!/^P\d{3,5}$/.test(this.researchParticipant)||this.researchDone(task))return;
   if(this.researchManualActive)this.closeAssistant();
   this.cancelRequest();this.cancelRecording();this.assistantOpen=false;this.resetFilters();this.releaseNotice();this.commandUndo=[];this.assistantAnswer=null;this.analysisContext=null;this.detail=null;this.researchAnswer='';this.researchWorkload='';this.researchMessage='';
   const now=Date.now();this.researchClock=now;this.researchActive={task,participant:this.researchParticipant,started:now,started_perf:performance.now(),started_at:new Date(now).toISOString(),events:[],observer_errors:0,help_count:0,validation_failures:0};
   this.researchTimer=setInterval(()=>{this.researchClock=Date.now()},1000);
   if(task.type==='verify')this.startNoticeVerification(this.dataset.find(r=>r.id===task.notice_id));else this.page=2;
   if(task.condition==='voice_chart')this.openAssistant();
  },
  researchPanel(){this.page=6},
  async microphoneCheck(){await this.openAssistant();this.voiceSubmit=false;this.continuous=false;this.assistantText='';this.commandMessage='请点击开始录音，朗读“只看2025年的玩具”，说完后停止。可编辑转写，再发送。'},
  finishResearch(abandoned=false){
   const active=this.researchActive;if(!active)return;
   if(!abandoned&&(this.assistantBusy||this.assistantRecording)){this.researchMessage='请先结束录音或取消当前请求，再保存任务。';this.page=6;return}
   if(abandoned){this.cancelRequest?.();this.cancelRecording?.()}
   const success=!abandoned&&ResearchStudy.check(active.task,this,active.events,this.researchAnswer);
   if(!abandoned&&!success){active.validation_failures++;this.researchMessage='尚未达成任务目标，请继续操作；也可记录为未完成。';return}
   if(success&&!active.completed_ms){active.completed_ms=Date.now();active.completed_perf=performance.now()}
   if(!abandoned&&!/^[1-7]$/.test(String(this.researchWorkload))){this.researchMessage='已停止任务计时，请填写1—7分的任务负担评分。';this.page=6;return}
   const requests=active.events.filter(e=>e.kind==='request'),transcriptions=requests.filter(e=>e.request_kind==='transcribe'&&e.status==='ok').length;
   const record={trial_id:crypto.randomUUID(),participant:active.participant,condition:active.task.condition,variant:active.task.variant,block:active.task.block,schedule_key:active.task.key,task_id:active.task.id,task_type:active.task.type,study_id:recallResearch.study_id,data_version:recallResearch.data_version,started_at:active.started_at,finished_at:new Date().toISOString(),task_completed_at:active.completed_ms?new Date(active.completed_ms).toISOString():null,elapsed_ms:Math.max(0,Math.round((active.completed_perf||performance.now())-active.started_perf)),success,completion:abandoned?'not_completed':'completed',workload:abandoned?null:Number(this.researchWorkload),observer_errors:active.observer_errors,help_count:active.help_count,validation_failures:active.validation_failures,clarifications:active.events.filter(e=>e.kind==='clarification').length,correction_commands:active.events.filter(e=>e.kind==='command'&&e.correction).length,undo_count:active.events.filter(e=>e.kind==='command'&&e.action==='undo').length,transcript_edits:active.events.filter(e=>e.kind==='transcript_edit').length,retry_count:active.events.filter(e=>e.kind==='retry').length,request_failures:requests.filter(e=>!['ok','cancelled'].includes(e.status)).length,request_count:requests.length,transcription_count:transcriptions,text_fallback:active.task.condition==='voice_chart'&&transcriptions===0,events:active.events};
   this.researchRecords.push(record);this.closeAssistant?.();clearInterval(this.researchTimer);this.researchActive=null;this.researchMessage=success?'任务已校验并保存。':'已保存未完成记录。';this.page=6;
   try{localStorage.setItem('recall-study-v1',JSON.stringify(this.researchRecords))}catch(e){this.researchMessage+=' 本机存储不可用，请立即导出记录。'}
  },
  exportResearch(){const data={schema_version:'study-records-v1',study_id:recallResearch.study_id,data_version:recallResearch.data_version,records:this.researchRecords},url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='交互任务记录.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)},
  async importResearch(event){try{const file=event.target.files[0];if(!file)return;if(file.size>6000000)throw Error('记录文件超过6MB。');const data=JSON.parse(await file.text());if(data.schema_version!=='study-records-v1'||data.study_id!==recallResearch.study_id||!Array.isArray(data.records)||data.records.some(r=>!ResearchStudy.validateRecord(r)||r.data_version!==recallResearch.data_version))throw Error('记录格式或数据版本不匹配。');const seen=new Set(this.researchRecords.map(r=>r.trial_id));this.researchRecords.push(...data.records.filter(r=>!seen.has(r.trial_id)));localStorage.setItem('recall-study-v1',JSON.stringify(this.researchRecords));this.researchMessage='已合并任务记录。'}catch(e){this.researchMessage=e.message}finally{event.target.value=''}}
 },
 mounted(){try{const rows=JSON.parse(localStorage.getItem('recall-study-v1')||'[]');if(Array.isArray(rows))this.researchRecords=rows.filter(r=>ResearchStudy.validateRecord(r)&&r.data_version===recallResearch.data_version)}catch(e){}},
 beforeUnmount(){clearInterval(this.researchTimer)}
};
