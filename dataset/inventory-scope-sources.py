"""Inventory every local source; no network, no inferred non-disclosure."""
import hashlib, json, re, sys
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urljoin
sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parent
class Source(HTMLParser):
    def __init__(self):
        super().__init__(); self.cells=[]; self.cell=None; self.assets=[]; self.parts=[]; self.skip=0
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag in ('script','style'): self.skip+=1
        if tag in ('td','th'): self.cell=[]
        if tag in ('br','p') and self.cell is not None:self.cell.append(' ')
        target=a.get('src') if tag=='img' else a.get('href') if tag=='a' else None
        if target and (tag=='img' or re.search(r'\.(?:pdf|docx?|xlsx?|zip)(?:\?|$)',target,re.I)):
            self.assets.append({'kind':'image' if tag=='img' else 'attachment','target':target})
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.skip=max(0,self.skip-1)
        if tag in ('td','th') and self.cell is not None:
            self.cells.append(re.sub(r'\s+',' ',''.join(self.cell)).strip());self.cell=None
    def handle_data(self,s):
        if not self.skip:
            self.parts.append(s)
            if self.cell is not None:self.cell.append(s)
def build(rows=None):
    result={};cached={}
    for ledger in ROOT.glob('*image-ledger.json'):
        for item in json.loads(ledger.read_text(encoding='utf-8')):
            if item.get('file') and item.get('source_url'):
                file=(ROOT/item['file']).resolve()
                if file.is_relative_to(ROOT) and file.is_file():
                    sha=hashlib.sha256(file.read_bytes()).hexdigest()
                    if sha!=item['sha256']:raise ValueError('Image changed '+item['file'])
                    cached[item['source_url']]={'local_file':item['file'],'sha256':sha,'previous_ledger':ledger.name}
    for r in rows if rows is not None else json.loads((ROOT/'recalls-2023-2025.json').read_text(encoding='utf-8')):
        path=(ROOT/r['raw_file']).resolve()
        if not path.is_relative_to(ROOT):raise ValueError(r['id'])
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=r['sha256']:raise ValueError('Source changed '+r['id'])
        p=Source()
        if path.suffix.lower()=='.html':p.feed(raw.decode('utf-8'))
        assets=[]
        for a in p.assets:
            target=a['target'];local=(path.parent/target.split('?')[0]).resolve()
            url=urljoin(r['source_url'],target)
            assets.append({**a,'url':url,'local_file':str(local.relative_to(ROOT)) if local.is_relative_to(ROOT) and local.is_file() else None,**cached.get(url,{})})
        result[r['id']]={'raw_file':r['raw_file'],'sha256':r['sha256'],'cells':p.cells,'assets':assets,'text':re.sub(r'\s+',' ',''.join(p.parts)), 'status':'本轮自动解析本地HTML并校验SHA256；非人工复核'}
    (ROOT/'scope-source-inventory.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'sources':len(result),'cells':sum(bool(x['cells']) for x in result.values())},ensure_ascii=False))
if __name__=='__main__':build(json.load(sys.stdin) if '--stdin' in sys.argv else None)
