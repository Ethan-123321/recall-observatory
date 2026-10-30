import unittest,copy
from research.analyze import summarize,validate,TYPES
class ResearchAnalysisTests(unittest.TestCase):
    def data(self):
        rows=[]
        for condition,duration in [('manual',1000),('voice_chart',500)]:
            for i,kind in enumerate(sorted(TYPES)):
                rows.append(dict(trial_id=condition+kind,participant='P001',condition=condition,task_type=kind,success=True,elapsed_ms=duration,started_at=f'2026-10-24T12:00:0{i}Z',workload=3,data_version='a'*64))
        return dict(schema_version='study-records-v1',records=rows)
    def test_subject_aggregation_and_complete_pair(self):
        s=summarize(self.data());self.assertEqual(s['participant_count'],1);self.assertEqual(len(s['subjects']),2)
        self.assertEqual(s['conditions']['manual']['success_rate'],1);self.assertEqual(s['paired_mean_difference_ms'],-500)
    def test_failure_counted_not_hidden(self):
        data=self.data();data['records'][0]['success']=False;s=summarize(data)
        self.assertEqual(s['conditions']['manual']['success_rate'],.75);self.assertEqual(s['complete_pairs'],[])
    def test_first_trial_rule(self):
        data=self.data();r={**data['records'][0],'trial_id':'repeat','started_at':'2026-10-24T13:00:00Z','elapsed_ms':10};data['records'].append(r)
        s=summarize(data);self.assertEqual(s['repeated_trials'],1);self.assertEqual(s['conditions']['manual']['successful_time_ms'],1000)
    def test_empty_is_missing_not_zero_effect(self):
        s=summarize(dict(schema_version='study-records-v1',records=[]));self.assertIsNone(s['paired_mean_difference_ms']);self.assertIsNone(s['conditions']['manual']['success_rate']);self.assertTrue(s['warnings'])
    def test_reject_invalid_or_mixed_data(self):
        for key,value in [('elapsed_ms',float('nan')),('success','yes'),('participant','real name'),('condition','unknown'),('observer_errors',-1)]:
            d=self.data();d['records'][0][key]=value
            with self.assertRaises(ValueError):validate(d)
        d=self.data();d['records'][0]['data_version']='b'*64
        with self.assertRaises(ValueError):validate(d)
    def test_fallback_stays_visible(self):
        d=self.data();d['records'][-1]['text_fallback']=True;s=summarize(d)
        self.assertEqual(s['conditions']['voice_chart']['text_fallbacks'],1);self.assertTrue(s['warnings'])
if __name__=='__main__':unittest.main()
