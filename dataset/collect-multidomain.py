"""Collect bounded public 2023-2025 source directories. Cached, throttled, no credentials."""
from pathlib import Path
from urllib.request import urlopen,Request
from urllib.parse import urlencode,urljoin,urlsplit
from concurrent.futures import ThreadPoolExecutor
import json,re,hashlib,time,sys
ROOT=Path(__file__).resolve().parent
RAW=ROOT/'raw'/'multidomain';RAW.mkdir(exist_ok=True)
BASE='https://www.samrdprc.org.cn'
SOURCES={'consumer':BASE+'/fzlm/zhgg/xfpzhgg/index.html','cars':BASE+'/zhxx/jdczh/jdczh/index.html','food':BASE+'/zhxx/spxgcpzh/index.html'}
def fetch(url,path):
 if path.exists():return path.read_bytes()
 for attempt in range(3):
  try:
   with urlopen(Request(url,headers={'User-Agent':'RecallCourseResearch/1.0'}),timeout=35) as res:raw=res.read()
   path.write_bytes(raw);time.sleep(.25);return raw
  except Exception:
   if attempt==2:raise
   time.sleep(1+attempt)
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def catalogue(name,url):
 entry=fetch(url,RAW/(name+'-entry.html')).decode('utf-8')
 query=json.loads(re.search(r'queryData="([^"]+)"',entry)[1].replace("'",'"'))
 api=urljoin(BASE,re.search(r'url="([^"]+)" queryData=',entry)[1]);records=[];pages=[];page=1;total=None
 while total is None or len(records)<total:
  query['paramJson']=json.dumps({'pageNo':page,'pageSize':15,'search':json.dumps({'deployTime':'2023-01-01 - 2025-12-31'})})
  request=api+'?'+urlencode(query);path=RAW/f'{name}-list-{page:03}.json';raw=fetch(request,path);payload=json.loads(raw)
  assert payload['success'];html=payload['data']['html']
  params=json.loads(re.search(r'class="pagination" queryData="([^"]+)"',html)[1].replace("'",'"'));n=int(params['count'])
  assert total is None or total==n;total=n
  found=re.findall(r'<li><a href="([^"]+)" title="([^"]*)"[^>]*>.*?<span>(\d{4}-\d{2}-\d{2})</span></li>',html,re.S)
  if not found:
   dump(RAW/(name+'-unexpected.json'),payload);raise ValueError(f'{name}: unsupported list format; total={n}')
  for href,title,date in found:
   assert '2023-01-01'<=date<='2025-12-31',f'Date filter not applied: {date}'
   records.append({'source_url':urljoin(BASE,href),'title':title,'published_date':date,'source_channel':name,'catalogue_page':page})
  pages.append({'page':page,'count':len(found),'raw_file':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(raw).hexdigest(),'request_url':request})
  if page%10==0 or len(records)>=total:print(name,page,len(records),total,flush=True)
  page+=1
 assert len(records)==total and len({r['source_url'] for r in records})==total
 return {'source_url':url,'retrieved_date':'2026-10-22','filter':'2023-01-01 / 2025-12-31','total':total,'pages':pages,'records':records}
def detail(r):
 row=dict(r);name=urlsplit(r['source_url']).path.rsplit('/',1)[-1];path=RAW/name
 try:
  raw=fetch(r['source_url'],path);row.update(raw_file=str(path.relative_to(ROOT)),sha256=hashlib.sha256(raw).hexdigest(),retrieved_date='2026-10-22')
 except Exception as e:row['error']=type(e).__name__+': '+str(e)
 return row
if __name__=='__main__':
 sys.stdout.reconfigure(encoding='utf-8')
 names=sys.argv[1:] or list(SOURCES)
 for name in names:
  target=ROOT/(name+'-catalogue-2023-2025.json')
  if target.exists():cat=json.loads(target.read_text(encoding='utf-8'))
  else:cat=catalogue(name,SOURCES[name]);dump(target,cat)
  output=[]
  with ThreadPoolExecutor(max_workers=3) as pool:
   for row in pool.map(detail,cat['records']):
    output.append(row)
    if len(output)%75==0:dump(ROOT/(name+'-collected.json'),output);print(name,'details',len(output),'/',len(cat['records']),flush=True)
  dump(ROOT/(name+'-collected.json'),output);print(name,'complete',len(output),flush=True)

