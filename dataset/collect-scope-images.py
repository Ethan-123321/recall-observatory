"""Fetch source-linked scope attachments for three unresolved HTML records."""
import json,re,urllib.request,hashlib
from pathlib import Path
from urllib.parse import urljoin
p=Path(__file__).resolve().parent
q=json.loads((p/'semantic-review-queue.json').read_text(encoding='utf8'));out=[]
for i in [352,499,659]:
 r=q[i];s=(p/r['raw_file']).read_text(encoding='utf8')
 for j,link in enumerate(dict.fromkeys(re.findall(r'(?:href|src)=["\']([^"\']+\.(?:pdf|xlsx?|docx?|jpg|png))["\']',s,re.I))):
  url=urljoin(r['source_url'],link);f=p/'raw'/'review-images'/('scope-'+str(i)+'-'+str(j)+Path(link).suffix)
  item=dict(queue_index=i,id=r['id'],source_url=url,file=str(f.relative_to(p)))
  try:
   if not f.exists():f.write_bytes(urllib.request.urlopen(url,timeout=30).read())
   item['sha256']=hashlib.sha256(f.read_bytes()).hexdigest()
  except Exception as e:item['error']=str(e)
  out.append(item)
(p/'scope-image-ledger.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
print('Scope attachments:',len(out),'errors:',sum('error' in x for x in out))
