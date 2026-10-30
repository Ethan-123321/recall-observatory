/* Request and capture lifecycle. Diagnostics contain no utterances, keys or audio. */
const RecallVoiceRuntime={
 data:()=>({requestControllers:null,requestEvents:[],captureEpoch:0,assistantRetryKind:'command',analysisContext:null,conversationSelection:null,lastTranscribedText:''}),
 methods:{
  logRequest(event){this.requestEvents.push(event);this.requestEvents=this.requestEvents.slice(-100);this.studyEvent?.('request',{request_kind:event.kind,duration_ms:event.duration_ms,status:event.status})},
  async assistantApi(path,data,options={}){
   if(!this.requestControllers)this.requestControllers=Vue.markRaw(new Map());
   const id=crypto.randomUUID(),controller=new AbortController(),start=performance.now(),startedAt=new Date().toISOString();
   this.requestControllers.set(id,controller);let timeout=false,status='ok',serverId=null;
   const timer=setTimeout(()=>{timeout=true;controller.abort()},options.timeout||65000);
   try{
    const response=await fetch('/api/'+path,{method:options.method||'POST',headers:{'Content-Type':'application/json'},body:options.method==='GET'?undefined:JSON.stringify(data),signal:controller.signal});
    if(!response.headers.get('content-type')?.includes('application/json')){const e=Error('请通过本地服务打开平台；当前接口未返回JSON。');e.code='invalid_response';throw e}
    const value=await response.json();serverId=value.request_id||null;
    if(!response.ok){const e=Error(value.error||'请求失败，请重试。');e.code=value.error_type||'http_'+response.status;throw e}
    return value;
   }catch(original){
    const e=original.name==='AbortError'?Object.assign(Error(timeout?'请求超时，问题已保留，可重试。':'请求已取消，问题已保留。'),{code:timeout?'timeout':'cancelled'}):original;
    status=e.code||'network_error';if(!e.code)e.code=status;throw e;
   }finally{clearTimeout(timer);this.requestControllers.delete(id);this.logRequest({id,server_id:serverId,kind:path,started_at:startedAt,duration_ms:Math.round(performance.now()-start),status})}
  },
  async openAssistant(){this.assistantOpen=true;this.assistantError='';try{this.assistantStatus=await this.assistantApi('status',null,{method:'GET',timeout:8000})}catch(e){if(e.code!=='cancelled')this.assistantError=e.message}},
  cancelRequest(){
   if(['请求麦克风','正在处理录音'].includes(this.assistantStage)){this.captureEpoch++;this.assistantStream?.getTracks().forEach(t=>t.stop());this.assistantStream=null;this.assistantRecorder=null}
   this.continuous=false;clearTimeout(this.conversationTimer);this.commandEpoch++;this.requestControllers?.forEach(c=>c.abort());
   this.assistantBusy=false;this.assistantStage='已取消';this.commandMessage='已取消当前请求，问题已保留。';this.commandPending=null;this.stopSpeaking();
  },
  async retryAssistant(){if(this.assistantBusy)return;this.studyEvent?.('retry');if(this.assistantRetryKind==='recording')return this.startRecording();if(this.assistantRetryKind==='transcribe'&&this.assistantAudio)return this.transcribeAssistant();if(this.assistantRetryKind==='analyze')return this.analyzeAssistant(this.assistantNotice);return this.sendAssistant()},
  exportDiagnostics(){const url=URL.createObjectURL(new Blob([JSON.stringify({schema_version:'requests-v1',events:this.requestEvents},null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='请求耗时与失败类型.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)},
  async analyzeAssistant(notice=null){
   const epoch=this.commandEpoch,filters=this.currentFilters();this.assistantBusy=true;this.assistantStage='正在统计';this.assistantError='';this.assistantNotice=notice;this.assistantAnswer=null;this.assistantRetryKind='analyze';
   try{const result=await this.assistantApi('analyze',{text:notice?'解释这条公告的范围条件和需要核对的信息':this.assistantText||'哪个月最多',filters,notice_id:notice?.id});
    if(epoch!==this.commandEpoch||!this.assistantOpen)return;
    result.snapshot=JSON.stringify(filters);this.assistantAnswer=result;this.analysisContext={filters,metric:result.facts.metric};this.assistantStage='已更新';
   }catch(e){if(epoch===this.commandEpoch){this.assistantError=e.message;this.continuous=false;this.assistantStage='可重试'}}finally{if(epoch===this.commandEpoch)this.assistantBusy=false}
  },
  async startRecording(){
   if(this.assistantBusy||this.assistantRecording)return;
   const capture=++this.captureEpoch;this.assistantRetryKind='recording';this.recordCancelled=false;this.heardVoice=false;this.lastVoiceAt=Date.now();this.assistantStage='请求麦克风';this.stopSpeaking();this.assistantBusy=true;this.assistantError='';this.assistantAudio=null;this.assistantPending=null;this.assistantSeconds=0;
   try{
    if(!navigator.mediaDevices?.getUserMedia||!window.MediaRecorder)throw Error('当前浏览器不支持录音，可继续输入文字。');
    const stream=await navigator.mediaDevices.getUserMedia({audio:true});
    if(capture!==this.captureEpoch||!this.assistantOpen){stream.getTracks().forEach(t=>t.stop());return}
    this.assistantStream=Vue.markRaw(stream);const recorder=new MediaRecorder(stream),chunks=[];this.assistantRecorder=Vue.markRaw(recorder);
    recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};
    recorder.onstop=async()=>{
     stream.getTracks().forEach(t=>t.stop());if(capture!==this.captureEpoch)return;
     this.stopMicMeter();clearInterval(this.assistantTimer);this.assistantRecording=false;this.assistantBusy=true;
     try{
      if(this.recordCancelled||!this.heardVoice){this.assistantAudio=null;return}
      this.assistantStage='正在处理录音';const audio=await this.audioToWav(new Blob(chunks,{type:recorder.mimeType}));
      if(capture!==this.captureEpoch||!this.assistantOpen)return;
      this.assistantAudio=audio;await this.transcribeAssistant();
     }catch(e){if(capture===this.captureEpoch)this.assistantError='录音处理失败，请重录或输入文字。'}
     finally{if(capture===this.captureEpoch){this.assistantBusy=false;this.assistantStream=null;this.assistantRecorder=null;this.scheduleListen()}}
    };
    recorder.start();this.assistantRecording=true;this.assistantStage='正在收音';this.startMicMeter(stream);this.assistantTimer=setInterval(()=>{this.assistantSeconds++;if(this.assistantSeconds>=60)this.stopRecording()},1000);
   }catch(e){if(capture===this.captureEpoch){this.assistantStream?.getTracks().forEach(t=>t.stop());this.assistantError=e.name==='NotAllowedError'?'麦克风未授权，可继续输入文字。':e.message;this.assistantStage='可重试';this.continuous=false;this.logRequest({id:crypto.randomUUID(),kind:'microphone',started_at:new Date().toISOString(),duration_ms:0,status:e.name==='NotAllowedError'?'permission_denied':'device_error'})}}
   finally{if(capture===this.captureEpoch)this.assistantBusy=false}
  },
  async transcribeAssistant(){
   if(!this.assistantAudio)return;const epoch=this.commandEpoch;this.assistantStage='正在转写';this.assistantBusy=true;this.assistantError='';this.assistantRetryKind='transcribe';
   try{const result=await this.assistantApi('transcribe',{audio:this.assistantAudio});if(epoch!==this.commandEpoch||!this.assistantOpen||this.recordCancelled)return;
    if(!result.text?.trim()){this.assistantRetryKind='recording';this.assistantAudio=null;this.logRequest({id:crypto.randomUUID(),kind:'transcribe_result',started_at:new Date().toISOString(),duration_ms:0,status:'no_speech'});throw Error('未识别出有效语音，请重新录音或编辑文字。')}
    this.assistantText=result.text;this.lastTranscribedText=result.text;this.assistantPending=null;this.assistantAudio=null;this.assistantBusy=false;this.assistantStage='转写完成，可编辑';
    if(this.voiceSubmit||this.continuous)await this.sendAssistant();
   }catch(e){if(epoch===this.commandEpoch){this.assistantError=e.message;this.continuous=false;this.assistantStage='可重试'}}finally{if(epoch===this.commandEpoch)this.assistantBusy=false}
  }
 },
 beforeUnmount(){this.commandEpoch++;this.captureEpoch++;this.requestControllers?.forEach(c=>c.abort())}
};
