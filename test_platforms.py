import unittest,json,io,base64
from unittest.mock import patch
import server
class PlatformTests(unittest.TestCase):
 def test_key_isolation(self):
  with patch.object(server,'settings',return_value={'provider':'bailian','key':'sk-existing'}):
   with self.assertRaises(ValueError):server.draft_settings({'provider':'siliconflow','key':'','text_model':'test/model'})
 def test_speech_multipart(self):
  c={'provider':'siliconflow','key':'sk-test-only','base':'https://api.siliconflow.cn/v1','asr_model':'FunAudioLLM/SenseVoiceSmall','text_model':'test/model'}
  with patch.object(server.urllib.request,'urlopen',return_value=io.BytesIO(b'{"text":"hello"}')) as call:
   result=server.qwen([{'content':[{'input_audio':{'data':'data:audio/wav;base64,'+base64.b64encode(b'RIFFtest').decode()}}]}],asr=True,config=c)
  req=call.call_args.args[0]
  self.assertEqual(result,'hello');self.assertTrue(req.full_url.endswith('/audio/transcriptions'));self.assertIn(b'RIFFtest',req.data);self.assertIn(b'name="model"',req.data)
 def test_text_json(self):
  c={'provider':'siliconflow','key':'sk-test-only','base':'https://api.siliconflow.cn/v1','text_model':'test/model'}
  with patch.object(server.urllib.request,'urlopen',return_value=io.BytesIO(b'{"choices":[{"message":{"content":"{}"}}]}')) as call:
   self.assertEqual(server.qwen([],config=c),'{}')
  self.assertEqual(json.loads(call.call_args.args[0].data)['response_format'],{'type':'json_object'})
if __name__=='__main__':unittest.main()
