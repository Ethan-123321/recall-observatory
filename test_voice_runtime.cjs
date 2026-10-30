const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {performance}=require('node:perf_hooks'),crypto=require('node:crypto');
const sandbox={Vue:{markRaw:x=>x},crypto,performance,AbortController,DOMException,setTimeout,clearTimeout,clearInterval,Date,nextTick:async f=>f?.(),window:{MediaRecorder:class{}},navigator:{mediaDevices:{}},fetch:null};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync('./dist/conversation.js','utf8')+';this.conversation=RecallConversation;',sandbox);
vm.runInContext(fs.readFileSync('./dist/voice-runtime.js','utf8')+';this.runtime=RecallVoiceRuntime;',sandbox);
const defaults={domain:'全部',year:'全部',query:'',category:'全部',risk:'全部',scope:'全部',from:'',to:'',month:''};
function view(){const x={...defaults,...sandbox.conversation.data(),...sandbox.runtime.data(),assistantOpen:true,assistantRecording:false,assistantText:'只看玩具',assistantHistory:[],dataset:[],paged:[],page:2,listPage:1,verifyResults:null,verifyQuery:'',verifyDomain:'全部',verifyModel:'',verifyDate:'',verifyBatch:'',stopSpeaking(){},stopMicMeter(){},currentFilters(){return Object.fromEntries(Object.keys(defaults).map(k=>[k,this[k]]))}};for(const mixin of [sandbox.conversation,sandbox.runtime])for(const [k,fn] of Object.entries(mixin.methods))x[k]=fn.bind(x);Object.defineProperty(x,'filtered',{get(){return []}});return x;}
(async()=>{
 const a=view();sandbox.fetch=async(url,options)=>new Promise((resolve,reject)=>options.signal.addEventListener('abort',()=>reject(new DOMException('aborted','AbortError'))));
 await assert.rejects(a.assistantApi('command',{text:'PRIVATE-INPUT'}, {timeout:10}),e=>e.code==='timeout');
 assert.equal(a.requestEvents[0].status,'timeout');assert.ok(!JSON.stringify(a.requestEvents).includes('PRIVATE-INPUT'));
 const b=view();let complete;b.assistantApi=()=>new Promise(r=>complete=r);const pending=b.sendAssistant();b.cancelRequest();complete({action:'search',filters:{...defaults,category:'玩具'},product:{}});await pending;assert.equal(b.category,'全部');assert.equal(b.assistantBusy,false);
 const c=view();let grant,stopped=0;sandbox.navigator.mediaDevices.getUserMedia=()=>new Promise(r=>grant=r);const capture=c.startRecording();c.cancelRequest();grant({getTracks:()=>[{stop(){stopped++}}]});await capture;assert.equal(stopped,1);assert.equal(c.assistantRecording,false);
 const d=view();d.assistantAudio='data:audio/wav;base64,test';d.recordCancelled=false;d.voiceSubmit=false;d.assistantApi=async()=>({text:'只看2025年的玩具'});await d.transcribeAssistant();assert.equal(d.assistantText,'只看2025年的玩具');assert.equal(d.assistantAudio,null);assert.equal(d.commandUndo.length,0);
 const e=view();e.assistantAudio='retained-for-retry';e.assistantApi=async()=>{throw Error('临时连接失败')};await e.transcribeAssistant();assert.equal(e.assistantAudio,'retained-for-retry');assert.equal(e.assistantRetryKind,'transcribe');
 console.log('PASS: timeout diagnostics, no input logging, cancelled responses ignored, microphone permission race and editable/retryable transcription');
})().catch(e=>{console.error(e);process.exitCode=1});
