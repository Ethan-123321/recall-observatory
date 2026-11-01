const RecallQualityView={
 data:()=>({qualityCapability:'',qualityField:'',qualityStatus:'',qualitySource:'',qualityPage:1,qualityBlocker:'',qualityChanged:false,qualityCompareStage:'after'}),
 computed:{
  qualityLedger(){return this.dataset.map(r=>({...RecallQuality.audit(r,RecallVerify),issue:r.scope_issue}))},
  qualityIndex(){return new Map(this.qualityLedger.map(r=>[r.id,r]))},
  qualityBase(){return this.filtered.map(r=>this.qualityIndex.get(r.id))},
  qualitySummary(){return RecallQuality.summary(this.qualityBase)},
  qualityBefore(){return Object.fromEntries(RecallQuality.capabilities.map(c=>[c,this.qualityBase.filter(r=>r.issue?.before===c).length]))},
  qualityDomainRows(){return ['一般消费品','汽车'].map(domain=>({domain,count:this.qualityBase.filter(r=>r.domain===domain).length,capabilities:RecallQuality.summary(this.qualityBase.filter(r=>r.domain===domain)).by_capability}))},
  qualityBlockerCounts(){const counts={};for(const r of this.qualityBase)for(const b of r.issue?.blockers||[])counts[b.label]=(counts[b.label]||0)+1;return Object.entries(counts).sort((a,b)=>b[1]-a[1])},
  qualityRows(){return this.qualityBase.filter(r=>(!this.qualityCapability||(this.qualityCompareStage==='before'?r.issue?.before:r.capability)===this.qualityCapability)&&(!this.qualityBlocker||r.issue?.blockers.some(b=>b.label===this.qualityBlocker))&&(!this.qualityChanged||r.issue?.before!==r.capability)&&(!this.qualitySource||r.source===this.qualitySource)&&(!this.qualityField||!this.qualityStatus||r.fields[this.qualityField].status===this.qualityStatus))},
  qualitySelectedSummary(){return RecallQuality.summary(this.qualityRows)},
  qualityPaged(){return this.qualityRows.slice((this.qualityPage-1)*20,this.qualityPage*20)},
  qualityPageCount(){return Math.max(1,Math.ceil(this.qualityRows.length/20))},
  qualityStatuses(){return RecallQuality.statuses},qualityCapabilities(){return RecallQuality.capabilities},qualityFields(){return RecallQuality.fields},
  qualityIssues(){return this.qualityRows.reduce((n,r)=>n+Object.values(r.fields).filter(f=>!['可直接使用','不适用'].includes(f.status)).length,0)}
 },
 watch:{qualityRows(){this.qualityPage=1}},
 methods:{
  clearQualityDrill(){this.qualityBlocker='';this.qualityChanged=false;this.qualityField='';this.qualityStatus='';this.qualitySource=''},
  openQualityDetails(){this.page=3;nextTick(()=>this.goSection('quality-overview'))},
  qualityRate(key){const c=this.qualitySummary.fields[key],den=this.qualityBase.length-c['不适用'];return den?`${c['可直接使用']} / ${den} (${(100*c['可直接使用']/den).toFixed(1)}%)`:'不适用'},
  selectQualityField(key,status){this.qualityField=key;this.qualityStatus=status;this.goSection('quality-records')},
  resetQuality(){this.resetFilters();this.qualityCapability='';this.qualityField='';this.qualityStatus='';this.qualitySource='';this.qualityBlocker='';this.qualityChanged=false;this.qualityCompareStage='after'},
  exportScopeIssues(){const url=URL.createObjectURL(new Blob([JSON.stringify(this.qualityRows.map(r=>r.issue),null,2)],{type:'application/json;charset=utf-8'})),a=document.createElement('a');a.href=url;a.download='逐条条件阻碍与处理记录.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)},
  drawScopeProgress(){
   if(this.$refs.qualityCompareChart){const c=this.chart('qualityCompareChart',{tooltip:{trigger:'axis'},legend:{data:['处理前','当前']},grid:{left:190,right:30,top:40,bottom:30},xAxis:{type:'value',minInterval:1},yAxis:{type:'category',data:RecallQuality.capabilities},series:[{name:'处理前',type:'bar',data:RecallQuality.capabilities.map(c=>this.qualityBefore[c]),itemStyle:{color:'#9ca8ad'}},{name:'当前',type:'bar',data:RecallQuality.capabilities.map(c=>this.qualitySummary.by_capability[c]||0),itemStyle:{color:'#547b64'}}]});c.on('click',p=>{this.clearQualityDrill();this.qualityCompareStage=p.seriesName==='处理前'?'before':'after';this.qualityCapability=p.name;this.goSection('quality-records')})}
   if(this.$refs.qualityBlockerChart){const entries=this.qualityBlockerCounts;this.$refs.qualityBlockerChart.style.height=Math.max(300,entries.length*42)+'px';const c=this.chart('qualityBlockerChart',{tooltip:{trigger:'axis'},grid:{left:240,right:50,top:15,bottom:25},xAxis:{type:'value',minInterval:1},yAxis:{type:'category',inverse:true,data:entries.map(x=>x[0]),axisLabel:{width:220,overflow:'break'}},series:[{type:'bar',data:entries.map(x=>x[1]),label:{show:true,position:'right'},itemStyle:{color:'#c49b55'}}]});c.on('click',p=>{this.clearQualityDrill();this.qualityCompareStage='after';this.qualityBlocker=p.name;this.qualityCapability='';this.goSection('quality-records')})}
  },
  qualityNotice(id){return this.dataset.find(r=>r.id===id)},
  exportQuality(){const blob=new Blob([RecallQuality.csv(this.qualityRows)],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='核验能力与字段台账.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)},
  drawQuality(){if(!this.$refs.qualityChart)return;this.dispose();const total=this.qualityBase.length;const chart=this.chart('qualityChart',{tooltip:{trigger:'axis',formatter:p=>p[0].name+'：'+p[0].value+'份'+(total?'（'+(100*p[0].value/total).toFixed(1)+'%）':'')},grid:{left:190,right:100,top:20,bottom:35},xAxis:{type:'value',minInterval:1,name:'去重公告 / 份'},yAxis:{type:'category',data:RecallQuality.capabilities,inverse:true,axisLabel:{fontSize:11}},series:[{type:'bar',data:RecallQuality.capabilities.map(c=>this.qualitySummary.by_capability[c]||0),label:{show:true,position:'right',formatter:p=>p.value+(total?' / '+(100*p.value/total).toFixed(1)+'%':'')},itemStyle:{color:'#547b64'},barMaxWidth:28}]});this.drawScopeProgress();chart.on('click',p=>{this.clearQualityDrill();this.qualityCompareStage='after';this.qualityCapability=this.qualityCapability===p.name?'':p.name;this.goSection('quality-records')})}
 }
};
