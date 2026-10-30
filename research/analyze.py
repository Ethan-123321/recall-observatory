"""Validate anonymous trial exports, aggregate by participant, and render figures."""
import argparse,json,math,re,statistics,datetime,hashlib
from pathlib import Path
TYPES={'filter','peak','verify','recover'}
CONDITIONS=['manual','voice_chart']
COUNT_FIELDS=['observer_errors','help_count','validation_failures','clarifications','correction_commands','undo_count','transcript_edits','retry_count','request_failures','request_count','transcription_count']
def mean(values):return statistics.mean(values) if values else None
def validate(payload):
    if payload.get('schema_version')!='study-records-v1' or not isinstance(payload.get('records'),list):raise ValueError('实验记录格式无效')
    rows=payload['records'];ids=set();versions=set()
    for r in rows:
        if not isinstance(r,dict) or not re.fullmatch(r'P\d{3,5}',str(r.get('participant',''))):raise ValueError('参与者编号无效')
        if r.get('condition') not in CONDITIONS or r.get('task_type') not in TYPES:raise ValueError('条件或任务类型无效')
        if type(r.get('success')) is not bool or type(r.get('elapsed_ms')) not in [int,float] or not math.isfinite(r['elapsed_ms']) or not 0<=r['elapsed_ms']<=86400000:raise ValueError('结果或用时无效')
        if not isinstance(r.get('trial_id'),str) or r['trial_id'] in ids:raise ValueError('记录ID缺失或重复')
        ids.add(r['trial_id'])
        if not re.fullmatch('[a-f0-9]{64}',str(r.get('data_version',''))):raise ValueError('数据版本无效')
        versions.add(r['data_version'])
        datetime.datetime.fromisoformat(r['started_at'].replace('Z','+00:00'))
        if r.get('workload') is not None and (type(r['workload']) not in [int,float] or not 1<=r['workload']<=7):raise ValueError('任务负担评分无效')
        for field in COUNT_FIELDS:
            if type(r.get(field,0)) is not int or r.get(field,0)<0:raise ValueError('计数字段无效：'+field)
    if versions and payload.get('data_version') and payload['data_version'] not in versions:raise ValueError('导出头部与记录的公告版本不一致')
    if len(versions)>1:raise ValueError('不能混合不同公告数据版本进行对比')
    return rows
def summarize(payload):
    raw=validate(payload);first={}
    for r in sorted(raw,key=lambda r:r['started_at']):first.setdefault((r['participant'],r['condition'],r['task_type']),r)
    rows=list(first.values());subjects=[]
    for participant in sorted({r['participant'] for r in rows}):
        for condition in CONDITIONS:
            group=[r for r in rows if r['participant']==participant and r['condition']==condition]
            if not group:continue
            subjects.append(dict(participant=participant,condition=condition,tasks=len(group),successes=sum(r['success'] for r in group),success_rate=sum(r['success'] for r in group)/len(group),successful_time_ms=mean([r['elapsed_ms'] for r in group if r['success']]),workload=mean([r['workload'] for r in group if r.get('workload') is not None]),text_fallbacks=sum(r.get('text_fallback',False) for r in group),**{field:sum(r.get(field,0) for r in group) for field in COUNT_FIELDS}))
    conditions={}
    for c in CONDITIONS:
        group=[r for r in subjects if r['condition']==c]
        conditions[c]=dict(participants=len(group),tasks=sum(r['tasks'] for r in group),success_rate=mean([r['success_rate'] for r in group]),successful_time_ms=mean([r['successful_time_ms'] for r in group if r['successful_time_ms'] is not None]),workload=mean([r['workload'] for r in group if r['workload'] is not None]),text_fallbacks=sum(r['text_fallbacks'] for r in group),**{field:sum(r[field] for r in group) for field in COUNT_FIELDS})
    paired=[]
    for participant in sorted({r['participant'] for r in rows}):
        groups={c:[r for r in rows if r['participant']==participant and r['condition']==c] for c in CONDITIONS}
        if all({r['task_type'] for r in groups[c]}==TYPES and all(r['success'] for r in groups[c]) for c in CONDITIONS):
            a,b=[mean([r['elapsed_ms'] for r in groups[c]]) for c in CONDITIONS]
            paired.append(dict(participant=participant,manual_ms=a,voice_chart_ms=b,difference_ms=b-a))
    warnings=[]
    if not rows:warnings.append('尚无真人任务记录，当前不计算交互收益。')
    if any(r.get('text_fallback') for r in rows):warnings.append('语音图表条件含文字回退；须与转写次数一并解释，不能将该条件全部视为实际语音使用。')
    if rows and not paired:warnings.append('尚无两条件四类任务均成功完成的参与者，未计算完整配对耗时差。')
    return dict(schema_version='study-summary-v1',study_id=payload.get('study_id'),data_version=next(iter({r['data_version'] for r in rows}),payload.get('data_version')),participant_count=len({r['participant'] for r in rows}),raw_trials=len(raw),analyzed_trials=len(rows),repeated_trials=len(raw)-len(rows),conditions=conditions,subjects=subjects,complete_pairs=paired,paired_mean_difference_ms=mean([r['difference_ms'] for r in paired]),warnings=warnings)
def render(summary,destination):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'svg.fonttype':'none'})
    fig,axes=plt.subplots(1,3,figsize=(12,3.7),layout='constrained');colors=['#547b64','#c49b55'];labels=['Manual','Voice + charts']
    for axis,key,title,scale in [(axes[0],'success_rate','Task success by participant',100),(axes[2],'workload','Reported task effort (1–7)',1)]:
        values=[[r[key]*scale for r in summary['subjects'] if r['condition']==c and r[key] is not None] for c in CONDITIONS]
        if not any(values):axis.text(.5,.5,'Awaiting participant records',ha='center',va='center',transform=axis.transAxes);axis.set_axis_off();continue
        for i,group in enumerate(values):
            if group:axis.bar(i,mean(group),color=colors[i],alpha=.55,width=.55);axis.scatter([i]*len(group),group,color=colors[i],edgecolor='white',s=34,zorder=3)
        axis.set_xticks([0,1],labels);axis.set_title(title);axis.spines[['top','right']].set_visible(False)
        axis.set_ylim((0,105) if key=='success_rate' else (0,7.5))
    axis=axes[1]
    if summary['complete_pairs']:
        for pair in summary['complete_pairs']:axis.plot([0,1],[pair['manual_ms']/1000,pair['voice_chart_ms']/1000],'-o',alpha=.7,color='#587e77')
        axis.set_xticks([0,1],labels);axis.set_ylabel('Seconds');axis.set_title('Complete paired task means');axis.spines[['top','right']].set_visible(False)
    else:axis.text(.5,.5,'Awaiting complete paired tasks',ha='center',va='center',transform=axis.transAxes);axis.set_axis_off()
    fig.suptitle(f'Interaction task study · n={summary["participant_count"]} participants')
    for ext in ['svg','png']:fig.savefig(destination/('interaction-results.'+ext),dpi=180)
    plt.close(fig)
def write_report(summary,destination):
    def fmt(v,scale=1,suffix=''):return '—' if v is None else f'{v*scale:.1f}{suffix}'
    lines=['# 交互任务对比报告','',f'参与者：{summary["participant_count"]}；原始记录：{summary["raw_trials"]}；主分析记录：{summary["analyzed_trials"]}。',f'重复记录：{summary["repeated_trials"]}；主分析采用每位参与者、每条件、每任务类型的首次记录。','',*summary['warnings'],'','| 条件 | 参与者 | 任务数 | 成功率（参与者均值） | 成功任务用时（参与者均值） | 费力程度 | 文字回退 |','| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for c,label in [('manual','手动筛选'),('voice_chart','语音＋图表')]:
        x=summary['conditions'][c];lines.append(f'| {label} | {x["participants"]} | {x["tasks"]} | {fmt(x["success_rate"],100,"%")} | {fmt(x["successful_time_ms"],.001,"秒")} | {fmt(x["workload"])} | {x["text_fallbacks"]} |')
    lines+=['',f'完整配对参与者：{len(summary["complete_pairs"])}；平均耗时差（语音图表−手动）：{fmt(summary["paired_mean_difference_ms"],.001,"秒")}。','', '失败任务计入成功率，不计入成功任务用时；完整配对耗时要求同一参与者在两个条件下四类任务均成功。任务记录先按参与者汇总，不把同一人多个任务当作独立受试者。费力程度为单题自报评分，不作为标准化量表结果。','', '本报告为描述性分析；任务材料、顺序、设备、接口和文字回退均可能影响结果。不得用工程接口测试替代真人实验。','',f'公告版本：{summary.get("data_version") or "尚未绑定记录"}。']
    (destination/'INTERACTION_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
def main():
    parser=argparse.ArgumentParser();parser.add_argument('records');parser.add_argument('--output',default='research/results');parser.add_argument('--no-plots',action='store_true');args=parser.parse_args()
    source=Path(args.records);destination=Path(args.output);destination.mkdir(parents=True,exist_ok=True)
    try:summary=summarize(json.loads(source.read_text(encoding='utf-8-sig')))
    except (ValueError,KeyError,TypeError) as e:parser.error(str(e))
    summary['source_file_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
    (destination/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');write_report(summary,destination)
    if not args.no_plots:render(summary,destination)
    print(f'Participants: {summary["participant_count"]}; analyzed tasks: {summary["analyzed_trials"]}')
if __name__=='__main__':main()
