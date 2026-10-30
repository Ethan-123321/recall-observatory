"""Deterministic conversational operations; context never supplies invented counts."""
import re, datetime, collections

def resolve(text, current, product, context, rows, categories, risks, domains, data_version):
    if not isinstance(context, dict) or set(context)-{'data_version','analysis_filters','analysis_metric','selected_notice_id','visible_ids','selected_month','selection_filters'}:
        raise ValueError('操作上下文格式无效。')
    if len(str(context))>12000:raise ValueError('操作上下文过长。')
    f=dict(current)
    def response(action='search', clarification='', **extra):
        return dict(action=action,filters=f,product=product,clarification=clarification,mode='local',**extra)
    def choose(question, options):return response(clarification=question,options=[dict(label=label,text=command) for label,command in options])
    def selected(filters):
        return [r for r in rows if (filters.get('domain','全部') in ['全部',r['domain']]) and (filters.get('year','全部') in ['全部',r['year']]) and (filters.get('category','全部') in ['全部',r['category']]) and (filters.get('risk','全部')=='全部' or filters['risk'] in r['risk_tags']) and (filters.get('scope','全部') in ['全部',r['scope_assessment']]) and (not filters.get('month') or r['published_date'].startswith(filters['month'])) and (not filters.get('from') or r['published_date']>=filters['from']) and (not filters.get('to') or r['published_date']<=filters['to']) and (not filters.get('query') or filters['query'].lower() in ' '.join(str(r.get(k) or '') for k in ['title','product_name','producer','brand','model_raw','production_dates_raw','defect_raw','batch_raw']).lower())]
    if text.strip() in ['撤销','撤销刚才的操作','撤销上一步','恢复上一步']:return response('undo')
    if re.search('打开|查看|列出',text) and re.search('公告|结果|这些产品|这条|那条',text):
        if context.get('data_version') and context['data_version']!=data_version:
            return choose('数据已更新，请重新统计后选择。',[('重新统计','哪个月最多？')])
        if re.search('这条|那条|当前公告',text):
            notice_id=context.get('selected_notice_id')
            if notice_id and any(r['id']==notice_id for r in rows):return response('open',target={'kind':'notice','notice_id':notice_id})
            return response(clarification='请先选中一条公告，或说“打开第一条公告”。')
        nth=re.search(r'第([一二三四五六七八九十\d]+)条',text)
        if nth:
            number={'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10}.get(nth[1],int(nth[1]) if nth[1].isdigit() else 0)
            visible=context.get('visible_ids',[])
            allowed={r['id'] for r in selected(f)}
            if not isinstance(visible,list) or len(visible)>20 or any(not isinstance(i,str) or i not in allowed for i in visible):raise ValueError('当前公告列表已变化，请重新打开列表。')
            if not 1<=number<=len(visible):return response(clarification='当前页没有这条公告，请选择可见结果。')
            return response('open',target={'kind':'notice','notice_id':visible[number-1]})
        explicit=re.search(r'(20\d{2})年(\d{1,2})月|(20\d{2})-(\d{2})(?!-\d)',text)
        month=None
        if explicit:
            year,m=(explicit[1],explicit[2]) if explicit[1] else (explicit[3],explicit[4]);month=f'{year}-{int(m):02d}'
            datetime.date.fromisoformat(month+'-01')
        elif re.search('那个月|这个月|该月|最多的月份',text):
            snapshot=context.get('analysis_filters')
            if f.get('month'):month=f['month']
            elif context.get('selected_month') and context.get('selection_filters')==f:
                month=context['selected_month'];datetime.date.fromisoformat(month+'-01')
            elif snapshot is not None:
                if context.get('analysis_metric') not in [None,'month']:return choose('上次统计未选中月份，请先查看月份统计。',[('统计最多月份','哪个月最多？')])
                if snapshot!=f:return choose('筛选已改变，请先更新统计。',[('重新统计','哪个月最多？')])
                counts=collections.Counter(r['published_date'][:7] for r in selected(f));top=max(counts.values(),default=0)
                winners=sorted(k for k,n in counts.items() if n==top)
                if len(winners)==1:month=winners[0]
                elif winners:return choose('有多个并列月份，请选择要打开的月份。',[(m,f'打开{m}的公告') for m in winners[:6]])
                else:return response(clarification='当前没有公告，请先调整筛选。')
            else:return choose('还没有选中的月份，请先统计或直接说出年月。',[('统计最多月份','哪个月最多？')])
        if month:f.update(month=month,year=month[:4] if month[:4] in {r['year'] for r in rows} else '全部',**{'from':'','to':''})
        return response('open',target={'kind':'list','month':month or ''})
    # Identifier changes are always reviewed in the product form before verification.
    identifiers={}
    for key,pattern in [('model',r'型号(?:是|为|改为|改成)?\s*([A-Za-z0-9_.*/+\-]+)'),('production',r'生产日期(?:是|为|改为|改成)?\s*(20\d{2}-\d{2}(?:-\d{2})?)'),('batch',r'批(?:号|次)(?:是|为|改为|改成)?\s*([A-Za-z0-9_./+\-]+)')]:
        match=re.search(pattern,text)
        if match:identifiers[key]=match[1]
    if identifiers:
        return dict(response('verify'),product={**product,**identifiers},question='请核对识别出的产品信息。')
    if re.search('核验|是否.*召回|查.*产品',text):return None
    if re.search('儿童用品',text):return choose('你要查看哪类儿童产品？',[(c,'只看'+c) for c in ['玩具','婴童用品','服饰鞋包']])
    corrected=re.search(r'不是(.+?)[，,\s]*(?:改成|改为|换成|换为|而是|是)(.+)',text)
    parse=corrected[2] if corrected else text
    if re.search('重置|全部公告|清空筛选',parse):
        f.update(domain='全部',year='全部',query='',category='全部',risk='全部',scope='全部',month='',**{'from':'','to':''})
        return response()
    changed=False
    year=re.search(r'(20\d{2})年',parse)
    if year:
        y=year[1];available={r['year'] for r in rows}
        f.update(year=y if y in available else '全部',month='',**{'from':'' if y in available else y+'-01-01','to':'' if y in available else y+'-12-31'})
        if '上半年' in parse:f.update(year='全部',**{'from':y+'-01-01','to':y+'-06-30'})
        if '下半年' in parse:f.update(year='全部',**{'from':y+'-07-01','to':y+'-12-31'})
        month=re.search(r'(\d{1,2})月',parse)
        if month:
            key=f'{y}-{int(month[1]):02d}';datetime.date.fromisoformat(key+'-01');f['month']=key
        changed=True
    for domain in domains:
        if domain in parse:f.update(domain=domain,category='全部');changed=True
    for key,values in [('category',categories),('risk',risks)]:
        matches=[value for value in values if value in parse]
        matches=[value for value in matches if not any(value!=other and value in other for other in matches)]
        if key=='risk' and not matches:
            aliases={'误吞':'窒息/误吞','火灾':'火灾/燃烧','燃烧':'火灾/燃烧','碰撞':'碰撞/失控风险'}
            matches=list(dict.fromkeys(aliases[word] for word in aliases if word in parse))
        if len(matches)>1:return choose('请指定一个筛选对象。',[(m,'只看'+m) for m in matches[:6]])
        if matches:
            f[key]=matches[0];changed=True
            if key=='category' and f['domain']!='全部' and not any(r['category']==f['category'] and r['domain']==f['domain'] for r in rows):f['domain']='全部'
    analysis=bool(re.search('哪个月|月份.*最多|每月|月度|什么风险最多|哪个风险|哪类.*最多|哪个类别|分析当前|总结当前|趋势',parse))
    if changed or analysis:return response('analyze' if analysis else 'search',question='已按当前任务更新条件。')
    return None
