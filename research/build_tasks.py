"""Freeze task materials and program-computed answer keys against one dataset."""
import json,hashlib,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def build():
    raw=(ROOT/'dataset/recalls-2023-2025.json').read_bytes();rows=json.loads(raw);by_id={r['id']:r for r in rows};tasks=[]
    for variant,year in [('A','2025'),('B','2024')]:
        filters={'year':year,'category':'玩具','risk':'机械伤害'}
        count=sum(r['year']==year and r['category']=='玩具' and '机械伤害' in r['risk_tags'] for r in rows)
        assert count>0, '实验筛选任务必须有实际公告'
        tasks.append(dict(id='filter-'+variant,variant=variant,type='filter',title='组合筛选',instruction=f'查找{year}年玩具类中涉及机械伤害风险的公告。',filters=filters,expected_count=count,expected_ids=[r['id'] for r in rows if r['year']==year and r['category']=='玩具' and '机械伤害' in r['risk_tags']]))
        selected=[r for r in rows if r['year']==year and r['category']=='玩具'];counts=collections.Counter(r['published_date'][:7] for r in selected);top=max(counts.values())
        tasks.append(dict(id='peak-'+variant,variant=variant,type='peak',title='图表追问',instruction=f'找出{year}年玩具公告最多的月份；如有并列，填写全部月份（YYYY-MM，用逗号分隔）。',filters={'year':year,'category':'玩具','risk':'全部','scope':'全部','query':'','month':'','from':'','to':''},expected_months=sorted(m for m,n in counts.items() if n==top),sample_count=len(selected),top_count=top))
        notice_id,model,production,batch=('art_31401ac19ceb420d8b83e702e9a890cf','MFZ/ABC4','2024-04-21','2024-04') if variant=='A' else ('art_280411cbe0554b1791251299bec3dc09','FV-15010','2021-05-07','20210507023')
        r=by_id[notice_id]
        tasks.append(dict(id='verify-'+variant,variant=variant,type='verify',title='复杂条件组核验',instruction=f'在“{r["title"]}”中核验型号{model}、生产日期{production}、批号{batch}，并展开至少一项对应原文证据。',notice_id=notice_id,product={'model':model,'production':production,'batch':batch},expected_state='matched',source_url=r['source_url'],source_sha256=r['sha256']))
        tasks.append(dict(id='recover-'+variant,variant=variant,type='recover',title='纠错与恢复',instruction=f'先筛选{year}年玩具中的机械伤害公告，再将风险改为“窒息/误吞”，最后恢复到机械伤害，并保留年份和类别。',filters={'year':year,'category':'玩具','risk':'机械伤害'},intermediate_risk='窒息/误吞'))
    manifest={'study_id':'recall-interaction-v1','data_version':hashlib.sha256(raw).hexdigest(),'date':'2026-10-24','conditions':['manual','voice_chart'],'tasks':tasks}
    (ROOT/'research/tasks.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    template=ROOT/'research/records-template.json'
    if not template.exists() or not json.loads(template.read_text(encoding='utf-8')).get('records'):
        template.write_text(json.dumps({'schema_version':'study-records-v1','study_id':manifest['study_id'],'data_version':manifest['data_version'],'records':[]},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'dist/research-tasks.js').write_text('const recallResearch = '+json.dumps(manifest,ensure_ascii=False)+';\n',encoding='utf-8')
    return manifest
if __name__=='__main__':print('Frozen tasks:',len(build()['tasks']))
