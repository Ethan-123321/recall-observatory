/* Context, action execution and undo; statistical answers come from the dataset. */
const RecallConversation={
 data:()=>({assistantStage:'',commandPending:null,commandMessage:'',autoStop:false,continuous:false,heardVoice:false,lastVoiceAt:0,recordCancelled:false,conversationTimer:null,commandUndo:[],commandEpoch:0}),
 watch:{detail(value){if(!value)this.scheduleListen()}},
 methods:{
  toggleContinuous(){clearTimeout(this.conversationTimer);if(this.continuous){this.autoStop=true;this.scheduleListen()}},
  productInput(){return {query:this.verifyQuery,domain:this.verifyDomain,model:this.verifyModel,production:this.verifyDate,batch:this.verifyBatch}},
  commandContext(){return {data_version:this.assistantStatus?.data_version,analysis_filters:this.analysisContext?.filters,analysis_metric:this.analysisContext?.metric,selected_notice_id:this.detail?.id||this.verifyFocus?.id||null,visible_ids:this.paged.map(r=>r.id),selected_month:this.conversationSelection?.month,selection_filters:this.conversationSelection?.filters}},
  rememberAction(){this.commandUndo.push({filters:this.currentFilters(),product:this.productInput(),page:this.page,noticeId:this.verifyNoticeId,verifyReturnPage:this.verifyReturnPage,results:this.verifyResults,detailId:this.detail?.id||null,listPage:this.listPage,answer:this.assistantAnswer,analysisContext:this.analysisContext,selection:this.conversationSelection,quality:{qualityCapability:this.qualityCapability,qualityField:this.qualityField,qualityStatus:this.qualityStatus,qualitySource:this.qualitySource}});this.commandUndo=this.commandUndo.slice(-10)},
  async sendAssistant(){
   if(this.assistantBusy||!this.assistantText.trim())return;
   this.stopSpeaking();this.commandPending=null;this.assistantPending=null;this.assistantError='';this.assistantBusy=true;this.assistantStage='正在理解';this.assistantRetryKind='command';
   const epoch=++this.commandEpoch;
   try{
    const command=await this.assistantApi('command',{text:this.assistantText,filters:this.currentFilters(),product:this.productInput(),page:this.page,history:this.assistantHistory,context:this.commandContext()});
    if(epoch!==this.commandEpoch||!this.assistantOpen)return;
    if(command.clarification){this.studyEvent?.('clarification');this.commandPending=command;this.commandMessage=command.clarification;this.assistantStage='等待补充';this.continuous=false;this.addTurn(command.clarification);return}
    if(command.action==='verify'){this.commandPending=command;this.commandMessage='请核对型号、生产日期与批号，再确认核验。';this.assistantStage='等待确认';this.continuous=false;return}
    await this.executeCommand(command,epoch);
   }catch(e){if(epoch===this.commandEpoch){this.assistantError=e.message;this.assistantStage='可重试';this.continuous=false}}
   finally{if(epoch===this.commandEpoch){this.assistantBusy=false;this.scheduleListen()}}
  },
  chooseClarification(option){this.assistantText=option.text;this.commandPending=null;return this.sendAssistant()},
  addTurn(answer){this.assistantHistory.push({question:this.assistantText,answer:String(answer).slice(0,2500)});this.assistantHistory=this.assistantHistory.slice(-6)},
  filterDescription(){return [this.domain==='全部'?'':this.domain,this.year==='全部'?'':this.year+'年',this.category==='全部'?'':this.category,this.risk==='全部'?'':this.risk,this.month,this.query].filter(Boolean).join(' · ')||'全部公告'},
  async executeCommand(command,epoch=this.commandEpoch){
   if(epoch!==this.commandEpoch)return;
   this.studyEvent?.('command',{action:command.action,correction:/不是/.test(this.assistantText)});
   if(command.action==='undo'){this.undoAssistant();return}
   this.rememberAction();this.commandMessage='';
   if(command.action==='verify'){
    this.releaseNotice();this.page=0;this.verifyQuery=command.product.query;this.verifyDomain=command.product.domain;this.verifyModel=command.product.model;this.verifyDate=command.product.production;this.verifyBatch=command.product.batch;
    await nextTick();if(epoch!==this.commandEpoch)return;this.verifyAll();this.commandMessage='已检查 '+this.verifyCandidates.length+' 份相关公告，请查看条件组结果。';this.assistantStage='已更新';this.addTurn(this.commandMessage);this.assistantOpen=false;
   }else if(command.action==='open'&&command.target?.kind==='notice'){
    const notice=this.dataset.find(r=>r.id===command.target.notice_id);if(!notice)throw Error('公告已变化，请重新选择。');this.detail=notice;this.commandMessage='已打开：'+notice.product_name;this.assistantStage='已更新';this.addTurn(this.commandMessage);
   }else{
    this.detail=null;Object.assign(this,command.filters);this.page=command.action==='analyze'?1:2;
    if(command.target?.month)this.conversationSelection={month:command.target.month,filters:this.currentFilters()};
    await nextTick();if(epoch!==this.commandEpoch)return;
    if(command.action==='analyze'){
     await this.analyzeAssistant();if(epoch===this.commandEpoch&&this.assistantAnswer){this.addTurn(this.assistantAnswer.answer);this.speakAnswer(this.assistantAnswer.answer)}
    }else{
     this.commandMessage='已筛选：'+this.filterDescription()+'\n找到 '+this.filtered.length+' 份公告，可撤销。';this.assistantStage='已更新';this.addTurn(this.commandMessage);this.speakAnswer(this.commandMessage);
    }
   }
   this.commandPending=null;
  },
  async confirmCommand(){if(this.assistantBusy||!this.commandPending)return;this.assistantBusy=true;try{if(!this.commandPending.product.query.trim()&&!this.commandPending.product.model.trim()){this.assistantError='请填写产品名称或型号。';return}await this.executeCommand(this.commandPending)}catch(e){this.assistantError=e.message}finally{this.assistantBusy=false}},
  undoAssistant(){
   const previous=this.commandUndo.pop();if(!previous){this.commandMessage='没有可撤销的操作。';return}
   Object.assign(this,previous.filters,previous.quality||{});this.verifyQuery=previous.product.query;this.verifyDomain=previous.product.domain;this.verifyModel=previous.product.model;this.verifyDate=previous.product.production;this.verifyBatch=previous.product.batch;this.page=previous.page;this.commandPending=null;this.assistantStage='已恢复';
   nextTick(()=>{this.verifyNoticeId=previous.noticeId||'';this.verifyFocus=this.dataset.find(r=>r.id===this.verifyNoticeId)||null;this.verifyReturnPage=previous.verifyReturnPage??2;this.verifyResults=previous.results||null;this.listPage=previous.listPage||1;this.detail=this.dataset.find(r=>r.id===previous.detailId)||null;this.assistantAnswer=previous.answer||null;this.analysisContext=previous.analysisContext||null;this.conversationSelection=previous.selection||null});this.commandMessage='已恢复上一步条件与选中对象。';
  },
  cancelRecording(){this.recordCancelled=true;this.continuous=false;this.captureEpoch++;this.assistantRecorder?.state==='recording'&&this.assistantRecorder.stop();this.assistantStream?.getTracks().forEach(t=>t.stop());this.stopMicMeter();clearInterval(this.assistantTimer);this.assistantRecording=false;this.assistantBusy=false;this.assistantRecorder=null;this.assistantStream=null;this.assistantAudio=null;this.assistantStage='已取消录音'},
  scheduleListen(){clearTimeout(this.conversationTimer);if(this.continuous&&this.assistantOpen&&!this.detail&&!this.annualDetail&&!this.assistantBusy&&!this.assistantRecording&&!this.commandPending&&!this.assistantError){this.conversationTimer=setTimeout(()=>{if(window.speechSynthesis?.speaking)this.scheduleListen();else if(this.continuous&&this.assistantOpen)this.startRecording()},700)}},
  closeAssistant(){this.assistantOpen=false;this.cancelRequest();this.cancelRecording();this.configKey='';this.commandPending=null},
 },
 beforeUnmount(){clearTimeout(this.conversationTimer)}
};
