const RecallWorkbench={
 data:()=>({verifyQuery:'',verifyDomain:'全部',verifyModel:'',verifyDate:'',verifyBatch:'',verifyResults:null,verifyLimit:12,verifyFocus:null,verifyNoticeId:'',verifyReturnPage:2,reportYear:'2025',reportDomain:'全部',reportMonth:'',reportQuery:''}),
 computed:{
  verifyCandidates(){return this.verifyNoticeId?this.dataset.filter(r=>r.id===this.verifyNoticeId):RecallVerify.search(this.dataset,this.verifyQuery,this.verifyDomain,this.verifyQuery.trim()?'':this.verifyModel)},
  verifyVisible(){return this.verifyCandidates.slice(0,this.verifyLimit)},
  reportBase(){return this.dataset.filter(r=>r.year===this.reportYear&&(this.reportDomain==='全部'||r.domain===this.reportDomain))},
  reportMonths(){return Array.from({length:12},(_,i)=>{const month=this.reportYear+'-'+String(i+1).padStart(2,'0');return {month,count:this.reportBase.filter(r=>r.published_date.startsWith(month)).length}})},
  reportRows(){return RecallAnalysis.filter(this.reportBase,{query:this.reportQuery,month:this.reportMonth})},
  completeness(){const rows=this.filtered;return [{name:'有型号原文',value:rows.filter(r=>r.model_raw).length},{name:'可解析日期（含月精度）',value:rows.filter(r=>RecallVerify.groups(r).some(g=>g.dateSpec)).length},{name:'有批次原文',value:rows.filter(r=>r.batch_raw).length},{name:'有来源证据',value:rows.filter(r=>r.source_url&&r.sha256).length}]},
 },
 watch:{verifyQuery(){this.clearVerification()},verifyDomain(){this.clearVerification()},verifyModel(){this.verifyResults=null},verifyDate(){this.verifyResults=null},verifyBatch(){this.verifyResults=null},reportYear(){this.reportMonth='';this.renderReport()},reportDomain(){this.reportMonth='';this.renderReport()}},
 methods:{
  clearVerification(){this.verifyResults=null;this.verifyLimit=12;this.verifyFocus=null;this.verifyNoticeId=''},
  verifyAll(){if(!this.verifyNoticeId&&!this.verifyQuery.trim()&&!this.verifyModel.trim()){this.verifyResults=[];return}this.verifyResults=this.verifyCandidates.map(r=>RecallVerify.check(r,{model:this.verifyModel,production:this.verifyDate,batch:this.verifyBatch}));this.activeSection='verify-evidence';nextTick(()=>document.getElementById('verify-evidence')?.scrollIntoView({behavior:'smooth'}))},
  startNoticeVerification(r){if(this.page!==0)this.verifyReturnPage=this.page;this.detail=null;this.annualDetail=null;this.page=0;this.verifyDomain=r.domain;this.verifyQuery=r.brand||r.producer||r.product_name;const ms=RecallVerify.models(r.model_raw);this.verifyModel=ms?.length===1?ms[0]:'';this.verifyDate='';this.verifyBatch='';nextTick(()=>{this.verifyFocus=r;this.verifyNoticeId=r.id;this.verifyResults=null})},
  useCandidate(r){if(!this.verifyQuery.trim())this.verifyQuery=r.brand||r.producer||r.product_name;this.verifyFocus=r;const ms=RecallVerify.models(r.model_raw);if(ms?.length===1)this.verifyModel=ms[0];nextTick(()=>{this.verifyFocus=r;this.verifyNoticeId=r.id;this.verifyResults=null})},
  releaseNotice(){this.verifyNoticeId='';this.verifyFocus=null;this.verifyResults=null},
  returnFromVerification(){this.page=this.verifyReturnPage},
  exportVerification(){const url=URL.createObjectURL(new Blob([JSON.stringify(this.verifyResults,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='产品核验结果与证据.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)},
  renderReport(){nextTick(()=>{if(this.page!==4||!this.$refs.reportChart)return;this.dispose();const c=this.chart('reportChart',{tooltip:{trigger:'axis'},grid:{left:45,right:25,bottom:40,top:30},xAxis:{type:'category',data:this.reportMonths.map(m=>m.month)},yAxis:{type:'value',minInterval:1,name:'去重公告 / 份'},series:[{type:'bar',data:this.reportMonths.map(m=>m.count),itemStyle:{color:'#547b64'},label:{show:true,position:'top'}}]});c.on('click',p=>this.reportMonth=this.reportMonth===p.name?'':p.name)})},
  showReportInSearch(){this.year=this.reportYear;this.domain=this.reportDomain;this.month=this.reportMonth;this.query=this.reportQuery;this.category='全部';this.risk='全部';this.scope='全部';this.from='';this.to='';this.page=2},
  highlightedParts(text){const q=this.query.trim();if(!q)return [{text:String(text||''),hit:false}];const s=String(text||''),i=s.toLowerCase().indexOf(q.toLowerCase());return i<0?[{text:s,hit:false}]:[{text:s.slice(0,i),hit:false},{text:s.slice(i,i+q.length),hit:true},{text:s.slice(i+q.length),hit:false}]}
 }
};
