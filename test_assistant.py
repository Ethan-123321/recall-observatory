import unittest, json, os, uuid
from pathlib import Path
from unittest.mock import patch
import server

class AssistantTests(unittest.TestCase):
    def setUp(self):
        self.test_path=Path(__file__).resolve().parent/('.test-config-'+uuid.uuid4().hex+'.json')
        self.config_patch=patch.object(server,'CONFIG_PATH',self.test_path)
        self.config_patch.start()
    def tearDown(self):
        self.config_patch.stop()
        self.test_path.unlink(missing_ok=True)
        self.test_path.with_suffix('.tmp').unlink(missing_ok=True)
    def test_save_private_and_blank_retains(self):
        payload={'key':'sk-test-secret-only','region':'beijing','text_model':'qwen-plus'}
        status=server.save_settings(payload)
        self.assertTrue(status['configured'])
        self.assertNotIn('sk-test',json.dumps(status))
        server.save_settings({**payload,'key':'','region':'singapore'})
        self.assertEqual(server.settings()['key'],payload['key'])
        self.assertEqual(server.settings()['base'],server.REGIONS['singapore'])
    def test_test_does_not_save(self):
        with patch.object(server,'qwen',return_value='{"ok":true}') as mock:
            result=server.test_settings({'key':'sk-test-only','region':'beijing','kind':'text'})
        self.assertTrue(result['ok']);self.assertFalse(server.CONFIG_PATH.exists())
        self.assertEqual(mock.call_args.kwargs['config']['key'],'sk-test-only')
    def test_speech_probe_and_invalid_config(self):
        with patch.object(server,'qwen',return_value='') as mock:
            server.test_settings({'key':'sk-test-only','region':'beijing','kind':'asr'})
        self.assertTrue(mock.call_args.kwargs['asr'])
        audio=mock.call_args.args[0][0]['content'][0]['input_audio']['data']
        self.assertTrue(audio.startswith('data:audio/wav;base64,'))
        for data in [{'key':'bad\nkey','region':'beijing'},{'key':'sk-test-only','region':'evil'}]:
            with self.assertRaises(ValueError):server.draft_settings(data)

    def test_local_preview(self):
        with patch.dict(os.environ,{'DASHSCOPE_API_KEY':''}):
            r=server.intent('2025年下半年玩具误吞风险',{})
        self.assertEqual(r['mode'],'local')
        self.assertEqual(r['filters']['from'],'2025-07-01')
        self.assertEqual(r['filters']['to'],'2025-12-31')
        self.assertEqual(r['filters']['category'],'玩具')
        self.assertEqual(r['filters']['risk'],'窒息/误吞')
    def test_ambiguous_and_context(self):
        with patch.dict(os.environ,{'DASHSCOPE_API_KEY':''}):
            self.assertTrue(server.intent('儿童用品',{})['clarification'])
            r=server.intent('哪个月最多',{'category':'玩具','from':'2025-01-01'})
        self.assertEqual(r['filters']['category'],'玩具')
        self.assertEqual(r['filters']['from'],'2025-01-01')
    def test_validation(self):
        for value in [{'category':'未知类'},{'from':'2025-02-30'},{'from':'2025-12-01','to':'2025-01-01'},{'sql':'DROP TABLE'},{'month':'2025-13'},{'risk':['触电']}]:
            with self.assertRaises(ValueError):server.validate(value)
    def test_empty_and_evidence(self):
        with patch.dict(os.environ,{'DASHSCOPE_API_KEY':''}):
            result=server.analyze('哪个月最多',{'query':'不存在的商品X987'})
        self.assertEqual(result['facts']['count'],0)
        self.assertEqual(result['evidence'],[])
        self.assertEqual(result['facts']['top_months'],[])
    def test_model_cannot_invent_evidence(self):
        with patch.dict(os.environ,{'DASHSCOPE_API_KEY':'test-only'}),patch.object(server,'qwen',return_value=json.dumps({'answer':'解释','evidence_ids':['forged']})):
            with self.assertRaises(ValueError):server.analyze('分析',{})
    def test_cloud_intent_contract(self):
        payload={'filters':{**server.DEFAULT,'category':'玩具'},'question':'确认玩具','clarification':''}
        with patch.dict(os.environ,{'DASHSCOPE_API_KEY':'test-only'}),patch.object(server,'qwen',return_value=json.dumps(payload)):
            r=server.intent('看看玩具',{})
        self.assertEqual(r['mode'],'qwen')
        self.assertEqual(r['filters']['category'],'玩具')
    def test_cause_does_not_guess_from_examples(self):
        with patch.object(server,'configured',return_value=True),patch.object(server,'qwen') as api:
            result=server.analyze('最多的召回原因是什么',{})
        api.assert_not_called()
        self.assertIn('不能确定',result['answer'])
        self.assertFalse(result['facts']['cause_classification_available'])
        self.assertEqual(result['facts']['metric'],'cause')

    def test_rankings_use_all_filtered_rows(self):
        with patch.object(server,'configured',return_value=False):
            result=server.analyze('什么风险最多',{'category':'玩具'})
        rows=[r for r in server.ROWS if r['category']=='玩具']
        expected=server.collections.Counter(t for r in rows for t in set(r['risk_tags']))
        self.assertEqual({r['name']:r['count'] for r in result['facts']['ranking']},dict(expected))
        self.assertEqual(result['facts']['count'],len(rows))
        self.assertEqual(server.ranking([{'risk_tags':['甲','甲','乙']}],'risk'),[{'name':'乙','count':1,'percent':100.0},{'name':'甲','count':1,'percent':100.0}])

    def test_tied_months_and_empty(self):
        rows=[{'published_date':'2025-01-01','category':'玩具','risk_tags':['甲']},{'published_date':'2025-02-01','category':'玩具','risk_tags':['乙']}]
        with patch.object(server,'ROWS',rows),patch.object(server,'configured',return_value=False):
            r=server.analyze('哪个月最多',{})
            self.assertIn('2025-01、2025-02',r['answer'])
            self.assertEqual(r['facts']['ranking'][0]['percent'],50.0)
            empty=server.analyze('最多的召回原因',{'query':'不存在'})
            self.assertEqual(empty['facts']['ranking'],[])

    def test_followup_context_reaches_model(self):
        payload={'filters':dict(server.DEFAULT),'question':'追问','clarification':''}
        history=[{'question':'看看玩具','answer':'当前玩具公告'}]
        with patch.object(server,'configured',return_value=True),patch.object(server,'qwen',return_value=json.dumps(payload)) as mock:
            server.intent('其中触电的呢',{},history)
        self.assertIn('看看玩具',json.dumps(mock.call_args.args[0],ensure_ascii=False))
        self.assertIn('其中触电的呢',json.dumps(mock.call_args.args[0],ensure_ascii=False))

    def test_relative_year_overrides_wrong_model_year(self):
        payload={'filters':{**server.DEFAULT,'from':'2023-01-01','to':'2023-12-31','month':'2023-03'},'question':'去年','clarification':''}
        with patch.object(server,'shanghai_today',return_value=server.datetime.date(2026,10,22)),patch.object(server,'configured',return_value=True),patch.object(server,'qwen',return_value=json.dumps(payload)) as api:
            r=server.intent('看看去年玩具里有触电风险的召回',{})
        self.assertEqual(r['filters']['from'],'2025-01-01')
        self.assertEqual(r['filters']['to'],'2025-12-31')
        self.assertEqual(r['filters']['month'],'')
        self.assertIn('2026-10-22',api.call_args.args[0][0]['content'])
    def test_relative_year_local_and_history(self):
        with patch.object(server,'shanghai_today',return_value=server.datetime.date(2026,10,22)),patch.object(server,'configured',return_value=False):
            r=server.intent('去年下半年玩具',{},[{'question':'2023年','answer':'旧上下文'}])
        self.assertEqual(r['filters']['from'],'2025-07-01')
        self.assertEqual(r['filters']['to'],'2025-12-31')
        self.assertEqual(server.resolve_relative_year('去年3月',server.datetime.date(2026,1,1)),('2025年3月',None))

    def test_stats_equal_source(self):
        with patch.dict(os.environ,{'DASHSCOPE_API_KEY':''}):r=server.analyze('分析',{'category':'玩具'})
        expected=sum(x['category']=='玩具' for x in server.ROWS)
        self.assertEqual(r['facts']['count'],expected)
        self.assertEqual(sum(r['facts']['month_counts'].values()),expected)

    def test_notice_explanation_preserves_selected_evidence(self):
        notice=next(r for r in server.ROWS if r['id']=='art_ba8a048fc6e140f6a51074eed924ce9e')
        with patch.object(server,'configured',return_value=False):
            result=server.analyze('这条公告有什么风险',{},notice['id'])
        self.assertEqual([r['id'] for r in result['evidence']],[notice['id']])
        self.assertIn('review_stages',result['evidence'][0])
        self.assertIn('2023年4月26日',result['evidence'][0]['production_dates_raw'])

    def test_canonical_scope_and_accessory_search(self):
        f=server.validate({'domain':'汽车','query':'JTC 1619'})
        rows=server.select(f)
        self.assertEqual(len(rows),1)
        self.assertEqual((rows[0]['quantity'],rows[0]['quantity_unit']),(138,'件'))
        with patch.object(server,'configured',return_value=False):result=server.analyze('统计',f)
        self.assertEqual(result['facts']['count'],1)
        self.assertEqual(result['facts']['review_stages']['scope'],{'范围条件AI辅助复核':1})

if __name__=='__main__':unittest.main()
