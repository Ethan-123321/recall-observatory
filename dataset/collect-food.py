"""Bounded Fujian food-recall sample. Only explicit recall notices, not inspections."""
from pathlib import Path
import importlib.util,re,json,hashlib,sys,io
from urllib.parse import urljoin
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('collector',ROOT/'collect-multidomain.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
base='https://scjgj.fujian.gov.cn/zt/spzh/spzh/'
html=(m.RAW/'fujian-index.html').read_text(encoding='utf-8')
rows=[]
for href,title,date in re.findall(r'<li><a href="([^"]+)"\s+title="([^"]+)".*?(\d{4}-\d{2}-\d{2})\s*</',html,re.S):
 if not ('2023-01-01'<=date<='2025-12-31') or '召回' not in title or not href.endswith('.pdf'):continue
 url=urljoin(base,href);path=m.RAW/href.rsplit('/',1)[-1]
 try:
  raw=m.fetch(url,path);text='\n'.join(p.extract_text() or '' for p in PdfReader(io.BytesIO(raw)).pages)
  rows.append(dict(id='fj_'+path.stem,title=title,published_date=date,source_url=url,raw_file=str(path.relative_to(ROOT)),sha256=hashlib.sha256(raw).hexdigest(),source_text=text,retrieved_date='2026-10-23'))
 except Exception as e:rows.append(dict(source_url=url,error=str(e)))
 m.dump(ROOT/'food-fujian-collected.json',rows)
 print(len(rows),len(rows[-1].get('source_text','')),flush=True)
