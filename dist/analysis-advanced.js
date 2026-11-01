const RecallAdvancedAnalysis={
 data:()=>({riskTimeUnit:'month',riskValueMode:'count',compositionPeriod:'',abilityCategory:'',abilityCapability:'可进行部分条件比对'}),
 computed:{
  capabilityStack(){return RecallAnalysis.capabilityStack(this.filtered.map(r=>({...r,capability:this.qualityIndex.get(r.id).capability})),RecallQuality.capabilities)},
  riskComposition(){const periods=this.riskTimeUnit==='year'?(this.year==='全部'?[...this.years].sort():[this.year]):this.year==='全部'?this.months:Array.from({length:12},(_,i)=>this.year+'-'+String(i+1).padStart(2,'0'));return RecallAnalysis.riskComposition(this.filtered,this.riskTimeUnit,periods)},
  compositionSampleRows(){const x=this.riskComposition;return x.periods.map((period,i)=>({period,count:x.samples[i],labels:x.tagTotals[i]}))},
  qualityReasonCounts(){const counts=new Map();for(const r of this.qualityRows)for(const reason of new Set(r.reasons))counts.set(reason,(counts.get(reason)||0)+1);return [...counts].sort((a,b)=>b[1]-a[1])}
 },
 watch:{filtered(){if(this.abilityCategory&&!this.capabilityStack.categories.includes(this.abilityCategory))this.abilityCategory='';if(this.compositionPeriod&&!this.riskComposition.periods.includes(this.compositionPeriod))this.compositionPeriod=''},riskTimeUnit(){this.compositionPeriod='';nextTick(()=>this.draw())},riskValueMode(){nextTick(()=>this.draw())}},
 methods:{
  showCapabilityDetails(category,capability){if(!category||!RecallQuality.capabilities.includes(capability))return;this.category=category;this.qualityCompareStage='after';this.qualityBlocker='';this.qualityChanged=false;this.qualityCapability=capability;this.qualityField='';this.qualityStatus='';this.qualitySource='';this.page=3;nextTick(()=>this.goSection('quality-records'))},
  openRiskSlice(period,risk=''){if(!period)return;if(this.riskTimeUnit==='year'){this.year=period;this.month=''}else{this.year=period.slice(0,4);this.month=period}this.from='';this.to='';if(risk)this.risk=risk;this.page=2;nextTick(()=>this.goSection('search-results'))},
  drawAdvancedAnalysis(){
   if(!this.$refs.capabilityChart||!this.$refs.riskCompositionChart)return;
   const stack=this.capabilityStack,maxTotal=Math.max(1,...stack.totals);
   this.$refs.capabilityChart.style.height=Math.max(340,stack.categories.length*32+95)+'px';
   const capability=this.chart('capabilityChart',{color:['#547b64','#c49b55','#9ca8ad'],tooltip:{trigger:'axis',axisPointer:{type:'shadow'}},legend:{show:false},grid:{left:125,right:30,top:45,bottom:25},xAxis:{type:'value',minInterval:1,position:'top',name:'份'},yAxis:{type:'category',inverse:true,data:stack.categories,axisLabel:{fontSize:11}},series:stack.series.map(s=>({name:s.name,type:'bar',stack:'capability',barMaxWidth:23,data:s.values,label:{show:true,formatter:p=>p.value/maxTotal>=.06?p.value:''}}))});
   capability.on('click',p=>{if(p.value)this.showCapabilityDetails(p.name,p.seriesName)});
   const data=this.riskComposition,percent=this.riskValueMode==='percent';
   const chart=this.chart('riskCompositionChart',{color:['#406e57','#c59851','#7396a1','#a07a89','#6b8c43','#ba7753','#777fb0','#b8a45c','#4d8c83','#9b7861','#b2c799','#8ca9c4'],tooltip:{trigger:'axis',formatter:params=>{if(!params.length)return '';const i=params[0].dataIndex;return data.periods[i]+'<br>公告样本 n='+data.samples[i]+'；风险标签 '+data.tagTotals[i]+' 次<br>'+params.filter(p=>p.value).map(p=>p.seriesName+'：'+(percent?Number(p.value).toFixed(1)+'%':p.value+'次')).join('<br>')}},legend:{type:'scroll',bottom:0,textStyle:{fontSize:11}},dataZoom:data.periods.length>16?[{type:'slider',bottom:36,height:16}]:[],grid:{left:50,right:25,top:40,bottom:data.periods.length>16?130:100},xAxis:{type:'category',data:data.periods,axisLabel:{rotate:40,fontSize:10,formatter:(value,i)=>value+'\nn='+data.samples[i]}},yAxis:{type:'value',name:percent?'风险标签构成 / %':'风险标签数 / 次',max:percent?100:undefined,minInterval:percent?undefined:1},series:data.series.map(s=>({name:s.name,type:'bar',stack:'risk',barMaxWidth:35,data:percent?s.proportions:s.counts}))});
   chart.on('click',p=>{if(p.value)this.openRiskSlice(p.name,p.seriesName)});
  }
 }
};
