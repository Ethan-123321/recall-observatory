/* Pure analysis shared by UI and data checks. Counts are notice counts. */
const RecallAnalysis = (() => {
 function filter(rows,f){
  const q=(f.query||'').trim().toLowerCase();
  return rows.filter(r=>(!f.domain||f.domain==='全部'||r.domain===f.domain)&&(!f.year||f.year==='全部'||r.published_date.startsWith(f.year+'-'))&&(!f.category||f.category==='全部'||r.category===f.category)
   &&(!f.risk||f.risk==='全部'||r.risk_tags.includes(f.risk))
   &&(!f.scope||f.scope==='全部'||r.scope_assessment===f.scope)
   &&(!f.from||r.published_date>=f.from)&&(!f.to||r.published_date<=f.to)
   &&(!f.month||r.published_date.startsWith(f.month))
   &&(!q||[r.title,r.product_name,r.producer,r.brand,r.model_raw,r.production_dates_raw,r.defect_raw,r.batch_raw].join(' ').toLowerCase().includes(q)));
 }
 function counts(rows,key){const map=new Map();for(const r of rows){const values=Array.isArray(r[key])?r[key]:[r[key]];for(const v of new Set(values))if(v)map.set(v,(map.get(v)||0)+1)}return [...map].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0],'zh'));}
 function months(rows){if(!rows.length)return [];let dates=rows.map(r=>r.published_date).sort(),a=dates[0].slice(0,7),b=dates.at(-1).slice(0,7),out=[];while(a<=b){out.push(a);let [y,m]=a.split('-').map(Number);a=m===12?`${y+1}-01`:`${y}-${String(m+1).padStart(2,'0')}`}return out;}
 function units(rows){let map=new Map();for(const r of rows)if(r.quantity_unit&&Number.isFinite(r.quantity)){map.set(r.quantity_unit,(map.get(r.quantity_unit)||0)+r.quantity)}return [...map].sort((a,b)=>b[1]-a[1]);}
 function csv(rows){const keys=['id','domain','year','review_status','title','published_date','producer','product_name','brand','category','risk_tags','model_raw','production_dates_raw','batch_raw','scope_assessment','quantity_raw','quantity','quantity_unit','defect_raw','consequence_raw','remedy_raw','review_stages','source_url','sha256'];const cell=v=>{let s=Array.isArray(v)?v.join('；'):v&&typeof v==='object'?JSON.stringify(v):String(v??'');if(/^[=+@\-]/.test(s))s="'"+s;return '"'+s.replaceAll('"','""')+'"'};return '\ufeff'+[keys,...rows.map(r=>keys.map(k=>r[k]))].map(row=>row.map(cell).join(',')).join('\r\n');}
 function matrix(rows,categories,risks,percent=false){return categories.flatMap((c,i)=>{const group=rows.filter(r=>r.category===c);return risks.map((risk,j)=>{const count=group.filter(r=>r.risk_tags.includes(risk)).length;return [j,i,percent?(group.length?Math.round(count/group.length*1000)/10:0):count,count,group.length]})})}
 function capabilityStack(rows,capabilities){
  const categories=counts(rows,'category').map(x=>x[0]);
  if(rows.some(r=>!capabilities.includes(r.capability)))throw Error('公告缺少有效核验能力，拒绝统计');
  return {categories,totals:categories.map(c=>rows.filter(r=>r.category===c).length),series:capabilities.map(name=>({name,values:categories.map(c=>rows.filter(r=>r.category===c&&r.capability===name).length)}))};
 }
 function riskComposition(rows,unit='month',periods=null){
  const keys=periods|| (unit==='year'?[...new Set(rows.map(r=>r.published_date.slice(0,4)))].sort():months(rows));
  const risks=counts(rows,'risk_tags').map(x=>x[0]),groups=keys.map(k=>rows.filter(r=>r.published_date.startsWith(k)));
  const samples=groups.map(g=>g.length),tagTotals=groups.map(g=>g.reduce((n,r)=>n+new Set(r.risk_tags||[]).size,0));
  const values=risks.map(name=>({name,counts:groups.map(g=>g.filter(r=>r.risk_tags.includes(name)).length)}));
  return {periods:keys,risks,samples,tagTotals,series:values.map(s=>({...s,proportions:s.counts.map((n,i)=>tagTotals[i]?100*n/tagTotals[i]:0)}))};
 }
 return {filter,counts,months,units,csv,matrix,capabilityStack,riskComposition};
})();
if(typeof module!=='undefined')module.exports=RecallAnalysis;
