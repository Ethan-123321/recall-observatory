"""Explicit engineering probe using saved settings; never changes or prints credentials."""
import json,time,base64,re,wave,urllib.request
from pathlib import Path
import server

def run(audio_path, kinds=None):
    result={'date':'2026-10-24','configuration':server.public_settings(),'checks':[]}
    saved=server.ROOT/'docs/API_SMOKE.json'
    if kinds and saved.exists():result=json.loads(saved.read_text(encoding='utf-8'))
    for kind in kinds or ['text','asr']:
        start=time.monotonic()
        try:
            if kind=='text':
                text=server.qwen([{'role':'system','content':'只返回JSON对象 {"ok":true}。'},{'role':'user','content':'连接测试'}])
                passed=json.loads(text).get('ok') is True;details={'structured_output':passed}
            else:
                with wave.open(str(audio_path),'rb') as wav:
                    if wav.getnframes()==0 or wav.getframerate()!=16000 or wav.getnchannels()!=1:raise ValueError('WAV前置检查未通过。')
                audio='data:audio/wav;base64,'+base64.b64encode(Path(audio_path).read_bytes()).decode()
                if kind=='asr_http':
                    req=urllib.request.Request('http://127.0.0.1:8767/api/transcribe',data=json.dumps({'audio':audio}).encode(),headers={'Content-Type':'application/json'})
                    with urllib.request.urlopen(req,timeout=45) as response:text=json.load(response)['text']
                else:text=server.qwen([{'role':'user','content':[{'type':'input_audio','input_audio':{'data':audio}}]}],asr=True)
                passed='玩具' in text and bool(re.search('2025|二零二五|二〇二五',text))
                details={'audio_source':'Windows speech synthesis, Huihui, 16kHz mono WAV','expected':'只看二零二五年的玩具','transcription':text}
            check={'kind':kind,'ok':passed,'elapsed_ms':round((time.monotonic()-start)*1000),**details}
        except Exception as e:
            check={'kind':kind,'ok':False,'elapsed_ms':round((time.monotonic()-start)*1000),'error_type':server.error_type(str(e)),'message':str(e)}
        result['checks'].append(check);print(json.dumps(check,ensure_ascii=False),flush=True)
        (server.ROOT/'docs/API_SMOKE.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result

if __name__=='__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8');run(sys.argv[1],sys.argv[2:] or None)
