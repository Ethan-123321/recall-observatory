const source = (tail) => 'https://www.samrdprc.org.cn/xfpzh/xfpgnzh/202506/'+tail+'.html';
const notices = [
 {id:'romoss',brand:'罗马仕',category:'移动电源',date:'2025-06-16',region:'广东',risk:'燃烧',defect:'部分电芯原材料存在问题，使用中可能过热，极端情况下可能燃烧。',action:'公告提供免费更换或退货退款两种处理方式。',phone:'400-651-7000',url:source('t20250618_113642'),models:[
 {model:'PAC20-272',count:331578,ranges:[['2023-06-05','2023-07-28'],['2024-01-05','2024-02-08']],batch:'C14-P6/P7、M14-P6/P7、C13-P6/P7、M20-Q1/Q2、M14-Q1/Q2、C14-Q1/Q2',manual:true},
 {model:'PAC20-392',count:113253,ranges:[['2024-06-23','2024-07-31']],batch:'M14-Q6/Q7、C13-Q6/Q7、M20-Q6/Q7、M22-Q6/Q7',manual:true},
 {model:'PLT20A-152',count:46914,ranges:[['2023-08-01','2024-01-31']],batch:'M20-P8/Q1',manual:true}]},
 {id:'anker',brand:'安克',category:'移动电源',date:'2025-06-20',region:'湖南',risk:'燃烧',defect:'部分批次电芯可能在长时间使用后发生隔膜绝缘失效，引起过热或燃烧。',action:'公告提供退换货；需通过品牌官方渠道核实具体批次。',phone:'400-055-0036',url:source('t20250623_113683'),models:[
 {model:'A1257',count:31857,ranges:[['2024-05-01','2024-12-31']],manual:true},
 {model:'A1680',count:24480,ranges:[['2024-05-01','2024-05-31']],manual:true},
 {model:'A1681',count:223558,ranges:[['2024-05-01','2025-02-28']],manual:true},
 {model:'A1689',count:45438,ranges:[['2024-07-01','2025-02-28']],manual:true}]},
 {id:'yamaha',brand:'雅马哈',category:'电源适配器',date:'2025-06-12',region:'上海',risk:'火灾',defect:'插头材料中的成分与水分反应，可能引起短路、异常发热和熔化。',action:'公告要求立即停止使用，并提供免费更换适配器服务。当前办理情况需向厂家确认。',phone:'400-051-7700',url:source('t20250612_113629'),models:[{model:'PA-300C',count:23387,ranges:[['2010-07-01','2012-05-31']],batch:'XXXX0XXXXXX、XXXX1XXXXXX、XXXX21XXXXX 至 XXXX25XXXXX（详见原文）',manual:true}]},
 {id:'leying',brand:'乐莹',category:'移动电源',date:'2025-12-17',region:'河南',risk:'火灾',defect:'电池重物冲击项目不符合相关标准，在重物冲击下可能起火。',action:'公告提供免费退货、换货服务。',phone:'18838113043',url:'https://scjgj.pds.gov.cn/contents/14214/23805.html',models:[{model:'D18',count:400,ranges:[['2025-07-29','2025-07-29']]}]},
 {id:'heater',brand:'海心焰',category:'取暖器',date:'2026-06-26',region:'湖南',risk:'触电',defect:'结构、接地、电源连接等项目不符合相关标准，使用中可能触电。',action:'公告提供退货处理；可向销售门店或厂家查询。',phone:'17718977819',url:'https://amr.hunan.gov.cn/amr/ztx/qxcpzh/zhxx/snzh/202606/t20260629_34015199.html',models:[{model:'NDY-100 1000W',count:500,ranges:[['2025-09-19','2025-09-30']]}]},
 {id:'linxee',brand:'新联合众（生产者）',category:'移动电源',date:'2026-07-30',region:'北京',risk:'烫伤',defect:'接触温度限值不符合相关标准，可能烫伤使用者。',action:'公告要求立即停止使用，提供全额退款及必要费用承担。',phone:'15810096845',url:'https://scjgj.beijing.gov.cn/zwxx/gs/zhxxzx/202607/t20260731_4803344.html',models:[{model:'LS103XG',count:212,ranges:[['2025-08-25','2025-08-27']],batch:'SZF25070901-A',exactBatch:true}]}
];
const records=notices.flatMap(n=>n.models.map(m=>({...n,...m,key:n.id+'-'+m.model})));
function verifyRecord(record,date,batch){
 if(!date)return {state:'pending',title:'还需要生产日期',reason:'型号已对应到公告。填写铭牌上的生产日期，继续核对范围。'};
 if(!record.ranges.some(([a,b])=>date>=a&&date<=b))return {state:'outside',title:'日期不符合这条公告的范围',reason:'这只表示未符合当前公告条件，不代表产品安全，也不排除其他公告。'};
 if(record.exactBatch && !batch.trim())return {state:'pending',title:'日期符合，还需要核对批次',reason:'请查看产品铭牌或包装上的生产批次。'};
 if(record.exactBatch && batch.trim().toUpperCase()!==record.batch)return {state:'outside',title:'批次不符合这条公告的范围',reason:'请复查输入。未匹配本条公告不能作为产品安全结论。'};
 if(record.manual)return {state:'pending',title:'型号与日期符合，批次仍需确认',reason:'公告涉及部分批次。样例不自动推断批次简写或序列号范围，请向品牌官方渠道进一步确认。'};
 return {state:'matched',title:'符合这条公告列出的核验条件',reason:'已核对型号、生产日期'+(record.exactBatch?'及批次':'')+'。请查看原公告，并联系厂家确认召回办理方式。'};
}
if(typeof module!=='undefined')module.exports={notices,records,verifyRecord};
