const RecallQualityView={
 data:()=>({qualityCapability:'',qualityField:'',qualityStatus:'',qualitySource:'',qualityPage:1}),
 computed:{
  qualityLedger(){return this.dataset.map(r=>RecallQuality.audit(r,RecallVerify))},
  qualityIndex(){return new Map(this.qualityLedger.map(r=>[r.id,r]))},
  qualityBase(){return this.filtered.map(r=>this.qualityIndex.get(r.id))},
  qualitySummary(){return RecallQuality.summary(this.qualityBase)},
  qualityRows(){return this.qualityBase.filter(r=>(!this.qualityCapability||r.capability===this.qualityCapability)&&(!this.qualitySource||r.source===this.qualitySource)&&(!this.qualityField||!this.qualityStatus||r.fields[this.qualityField].status===this.qualityStatus))},
  qualitySelectedSummary(){return RecallQuality.summary(this.qualityRows)},
  qualityPaged(){return this.qualityRows.slice((this.qualityPage-1)*20,this.qualityPage*20)},
  qualityPageCount(){return Math.max(1,Math.ceil(this.qualityRows.length/20))},
  qualityStatuses(){return RecallQuality.statuses},qualityCapabilities(){return RecallQuality.capabilities},qualityFields(){return RecallQuality.fields},
  qualityIssues(){return this.qualityRows.reduce((n,r)=>n+Object.values(r.fields).filter(f=>!['可直接使用','不适用'].includes(f.status)).length,0)}
 },
 watch:{qualityRows(){this.qualityPage=1}},
 methods:{
  openQualityDetails(){this.page=3;nextTick(()=>this.goSection('quality-overview'))},
  qualityRate(key){const c=this.qualitySummary.fields[key],den=this.qualityBase.length-c['不适用'];return den?`${c['可直接使用']} / ${den} (${(100*c['可直接使用']/den).toFixed(1)}%)`:'不适用'},
  selectQualityField(key,status){this.qualityField=key;this.qualityStatus=status;this.goSection('quality-records')},
  resetQuality(){this.resetFilters();this.qualityCapability='';this.qualityField='';this.qualityStatus='';this.qualitySource=''},
  qualityNotice(id){return this.dataset.find(r=>r.id===id)},
  exportQuality(){const blob=new Blob([RecallQuality.csv(this.qualityRows)],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='核验能力与字段台账.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)},
  drawQuality(){if(!this.$refs.qualityChart)return;this.dispose();const total=this.qualityBase.length;const chart=this.chart('qualityChart',{tooltip:{trigger:'axis',formatter:p=>p[0].name+'：'+p[0].value+'份'+(total?'（'+(100*p[0].value/total).toFixed(1)+'%）':'')},grid:{left:190,right:100,top:20,bottom:35},xAxis:{type:'value',minInterval:1,name:'去重公告 / 份'},yAxis:{type:'category',data:RecallQuality.capabilities,inverse:true,axisLabel:{fontSize:11}},series:[{type:'bar',data:RecallQuality.capabilities.map(c=>this.qualitySummary.by_capability[c]||0),label:{show:true,position:'right',formatter:p=>p.value+(total?' / '+(100*p.value/total).toFixed(1)+'%':'')},itemStyle:{color:'#547b64'},barMaxWidth:28}]});chart.on('click',p=>{this.qualityCapability=this.qualityCapability===p.name?'':p.name;this.goSection('quality-records')})}
 }
};
