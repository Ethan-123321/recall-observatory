"""Download image bodies only for the unresolved source ledger, without cloud APIs."""
from pathlib import Path
from urllib.parse import urljoin,urlsplit
import json,re,hashlib,importlib.util,sys
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('collector',ROOT/'collect-multidomain.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
OUT=ROOT/'raw'/'review-images';OUT.mkdir(exist_ok=True)
rows=json.loads((ROOT/'excluded-multidomain.json').read_text(encoding='utf-8'))
tasks=[]
for r in rows:
 if not r.get('raw_file','').endswith('.html'):continue
 html=(ROOT/r['raw_file']).read_text(encoding='utf-8');body=html.split('id="zoom">',1)[-1].split('<script>',1)[0]
 for n,src in enumerate(re.findall(r'<img[^>]+src="([^"]+)"',body)):
  url=urljoin(r['source_url'],src);path=OUT/(r['id']+'-'+str(n)+Path(urlsplit(url).path).suffix)
  tasks.append(dict(id=r['id'],source_url=url,path=str(path),file=str(path.relative_to(ROOT))))
def fetch(r):
 try:raw=c.fetch(r['source_url'],Path(r['path']));r['sha256']=hashlib.sha256(raw).hexdigest()
 except Exception as e:r['error']=str(e)
 return r
result=[]
with ThreadPoolExecutor(max_workers=3) as pool:
 for r in pool.map(fetch,tasks):
  result.append(r)
  if len(result)%20==0:print(len(result),'/',len(tasks),flush=True);c.dump(ROOT/'review-image-ledger.json',result)
c.dump(ROOT/'review-image-ledger.json',result)
