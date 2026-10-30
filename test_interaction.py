import unittest,copy
from unittest.mock import patch
import server

class InteractionTests(unittest.TestCase):
    def test_correct_year_discards_old_month(self):
        f=self.call('看看2025年的汽车召回')['filters']
        f=self.call('只看燃烧风险',f)['filters']
        f=self.call('打开2025年1月的公告',f)['filters']
        for phrase in ['不是2025年，改成2024年','不是2025年，改为2024年','不是2025年，而是2024年']:
            with self.subTest(phrase=phrase):
                g=self.call(phrase,f)['filters']
                self.assertEqual(g['year'],'2024')
                self.assertEqual(g['month'],'')
                self.assertEqual(g['from'],'')
                self.assertEqual(g['to'],'')
                self.assertEqual(g['domain'],f['domain'])
                self.assertEqual(g['category'],f['category'])
                self.assertEqual(g['risk'],f['risk'])
    def test_risk_filter_then_month_question(self):
        f=self.call('看看2025年的汽车召回')['filters']
        command=self.call('只看燃烧风险，哪个月最多？',f)
        self.assertEqual(command['action'],'analyze')
        result=server.analyze('只看燃烧风险，哪个月最多？',command['filters'])
        self.assertEqual(result['facts']['metric'],'month')
        expected=server.ranking(server.select(command['filters']),'month')
        self.assertEqual(result['facts']['ranking'],expected)
        opened=self.call('打开那个月的公告',command['filters'],{'analysis_filters':command['filters'],'analysis_metric':result['facts']['metric'],'data_version':server.DATA_VERSION})
        winners=[x['name'] for x in expected if x['count']==expected[0]['count']]
        if len(winners)==1:self.assertEqual(opened['filters']['month'],winners[0])
        else:self.assertEqual([x['label'] for x in opened['options']],winners[:6])
    def call(self,text,f=None,context=None):return server.command(text,{'filters':f or {},'context':context or {}})
    def test_filter_correct_preserves_context(self):
        f=self.call('只看2025年的玩具')['filters']
        self.assertEqual((f['year'],f['category']),('2025','玩具'))
        f=self.call('只看触电',f)['filters'];g=self.call('不是触电，是烫伤',f)['filters']
        self.assertEqual(g['risk'],'烫伤');self.assertEqual(g['year'],'2025');self.assertEqual(g['category'],'玩具')
    def test_known_commands_do_not_need_cloud(self):
        with patch.object(server,'qwen') as cloud:
            for text in ['只看2025年的玩具','哪个月最多？','不是触电，是烫伤','打开第一条公告']:
                self.call(text)
        cloud.assert_not_called()
    def test_peak_reference_recomputes_counts(self):
        f=self.call('只看2025年的玩具')['filters'];counts=server.collections.Counter(r['published_date'][:7] for r in server.select(f));winners=[m for m,n in counts.items() if n==max(counts.values())]
        r=self.call('打开那个月的公告',f,{'analysis_filters':f,'analysis_metric':'month','data_version':server.DATA_VERSION})
        if len(winners)==1:self.assertEqual(r['filters']['month'],winners[0]);self.assertEqual(r['action'],'open')
        else:self.assertEqual(len(r['options']),min(6,len(winners)))
    def test_stale_and_missing_reference(self):
        self.assertTrue(self.call('打开那个月的公告')['clarification'])
        self.assertTrue(self.call('打开那个月的公告',{'category':'玩具'},{'analysis_filters':server.DEFAULT})['clarification'])
        self.assertTrue(self.call('打开那个月的公告',context={'data_version':'old'})['clarification'])
    def test_tie_requires_choice(self):
        rows=[{**server.ROWS[0],'id':'one','published_date':'2025-01-01','year':'2025'},{**server.ROWS[0],'id':'two','published_date':'2025-02-01','year':'2025'}]
        with patch.object(server,'ROWS',rows):r=self.call('打开那个月的公告',context={'analysis_filters':dict(server.DEFAULT)})
        self.assertEqual([x['label'] for x in r['options']],['2025-01','2025-02'])
    def test_open_visible_notice_and_reject_stale_ids(self):
        f=server.validate({'category':'玩具'});notice=server.select(f)[0]
        r=self.call('打开第一条公告',f,{'visible_ids':[notice['id']]})
        self.assertEqual(r['target']['notice_id'],notice['id'])
        with self.assertRaises(ValueError):self.call('打开第一条公告',f,{'visible_ids':['forged']})
    def test_identifier_changes_are_confirmable(self):
        r=self.call('型号A1，生产日期2024-02，批号B01')
        self.assertEqual(r['action'],'verify');self.assertEqual(r['product']['production'],'2024-02');self.assertEqual(r['product']['model'],'A1')
        with self.assertRaises(ValueError):self.call('生产日期2024-02-30')
    def test_ambiguity_and_context_validation(self):
        self.assertEqual(len(self.call('只看儿童用品')['options']),3)
        with self.assertRaises(ValueError):self.call('打开公告',context={'sql':'delete'})
    def test_month_switch_clears_old_ranges(self):
        r=self.call('打开2025年7月的公告',{'year':'2024','from':'2024-01-01','to':'2024-12-31'})
        self.assertEqual(r['filters']['month'],'2025-07');self.assertEqual(r['filters']['from'],'')
    def test_source_version_and_undo(self):
        self.assertEqual(self.call('撤销上一步')['action'],'undo')
        self.assertEqual(self.call('只看玩具')['data_version'],server.DATA_VERSION)

if __name__=='__main__':unittest.main()
