"""Exercise the actual local HTTP task chain; never creates participant records."""
import json,urllib.request,time
from pathlib import Path
import server
def post(endpoint,body):
    request=urllib.request.Request('http://127.0.0.1:8767/api/'+endpoint,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    return json.load(urllib.request.urlopen(request,timeout=15))
def run():
    steps=[];f=server.validate({})
    empty_f=server.validate({'year':'2025','category':'玩具','risk':'触电'})
    empty=post('analyze',{'text':'哪个月最多？','filters':empty_f})
    assert empty['facts']['count']==0 and empty['facts']['top_months']==[]
    assert post('command',{'text':'打开那个月的公告','filters':empty_f,'context':{'analysis_filters':empty_f}})['clarification']
    steps.append({'step':'empty_result_recovery','count':0,'clarified':True})
    command=post('command',{'text':'只看2025年的家用电器触电','filters':f});f=command['filters'];assert f['category']=='家用电器' and f['risk']=='触电'
    steps.append({'step':'filter','count':len(server.select(f)),'filters':f,'elapsed_ms':command['elapsed_ms']})
    analysis=post('analyze',{'text':'哪个月最多？','filters':f});winners=analysis['facts']['top_months'];assert winners
    assert all(next(r for r in server.ROWS if r['id']==e['id'])['published_date'][:7] in winners for e in analysis['evidence'])
    steps.append({'step':'followup','months':winners,'count':analysis['facts']['top_count'],'elapsed_ms':analysis['elapsed_ms']})
    opened=post('command',{'text':'打开那个月的公告','filters':f,'context':{'data_version':server.DATA_VERSION,'analysis_filters':f,'analysis_metric':'month'}})
    if opened.get('options'):
        steps.append({'step':'clarify_tie','options':[x['label'] for x in opened['options']]})
        opened=post('command',{'text':opened['options'][0]['text'],'filters':f})
    f=opened['filters'];assert opened['action']=='open' and f['month'] in winners
    steps.append({'step':'open_month','month':f['month'],'count':len(server.select(f))})
    candidates=sorted(server.select(f),key=lambda r:r['published_date'],reverse=True)[:8]
    notice=post('command',{'text':'打开第一条公告','filters':f,'context':{'visible_ids':[r['id'] for r in candidates]}})
    assert notice['target']['notice_id']==candidates[0]['id'];steps.append({'step':'open_notice','id':notice['target']['notice_id']})
    corrected=post('command',{'text':'不是触电，是烫伤','filters':f});assert corrected['filters']['risk']=='烫伤' and corrected['filters']['month']==f['month']
    steps.append({'step':'correct','filters':corrected['filters']})
    undo=post('command',{'text':'撤销上一步','filters':corrected['filters']});assert undo['action']=='undo';steps.append({'step':'undo','action':undo['action']})
    result={'type':'engineering-http-task-check','date':'2026-10-24','data_version':server.DATA_VERSION,'passed':True,'steps':steps}
    (server.ROOT/'docs/INTERACTION_CHECK.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('PASS: live HTTP filter → followup → open month/notice → correction → undo')
if __name__=='__main__':run()
