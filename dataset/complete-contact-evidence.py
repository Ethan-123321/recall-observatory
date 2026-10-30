"""Extract explicitly labelled public recall contact cells, preserving provenance."""
import hashlib, importlib.util, re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('contact_page',ROOT/'collect-2025.py')
page=importlib.util.module_from_spec(spec);spec.loader.exec_module(page)
def apply(rows):
    for r in rows:
        source=ROOT/r.get('raw_file','')
        if source.suffix.lower()!='.html' or r.get('contact_raw'):continue
        raw=source.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=r['sha256']:raise ValueError('Contact source changed: '+r['id'])
        parser=page.Page();parser.feed(raw.decode('utf-8'))
        values=[]
        for i,cell in enumerate(parser.cells[:-1]):
            if re.sub(r'\s+','',cell) in ('召回联系方式','召回联系电话','联系人及联系方式'):
                value=parser.cells[i+1].strip()
                if 3<len(value)<1200 and re.search(r'\d[\d\s-]{5,}\d',value):values.append(value)
        if values:
            value='；'.join(dict.fromkeys(values));r['contact_raw']=value
            r.setdefault('field_review',{})['contact_raw']={'status':'官方HTML联系方式表格定点提取，非电话有效性验证','evidence':value,'source_sha256':r['sha256'],'locator':'召回联系方式表格单元格'}
    return rows
