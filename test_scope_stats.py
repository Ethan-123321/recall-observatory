"""Exercise the real stats endpoint without loading credentials or calling an AI service."""
import os
os.environ['RECALL_SKIP_ENV']='1'
import collections, json, sqlite3, threading, unittest, urllib.request
from pathlib import Path
import server
class StatsTest(unittest.TestCase):
    def test_filtered_stats_and_snapshot_parity(self):
        stats=server.capability_stats()
        self.assertEqual(stats['count'],len(server.ROWS))
        self.assertEqual(stats['after'],dict(collections.Counter(r['capability'] for r in json.loads((server.ROOT/'dataset/capability-ledger.json').read_text(encoding='utf-8')))))
        cars=[r for r in server.ROWS if r['domain']=='汽车']
        self.assertEqual(server.capability_stats(cars)['remaining_blockers']['需要官方VIN确认'],len(cars))
        self.assertNotIn('可进行确定性条件比对',server.capability_stats(cars)['after'])
        self.assertEqual(server.capability_stats([])['count'],0)
        with sqlite3.connect(server.ROOT/'dataset/recalls-2023-2025.sqlite3') as db:
            stored={id:json.loads(record) for id,record in db.execute('SELECT id,record_json FROM notices')}
        self.assertEqual(stored,{r['id']:r for r in server.ROWS})
    def test_live_http_endpoint(self):
        http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
        try:
            with urllib.request.urlopen('http://127.0.0.1:'+str(http.server_port)+'/api/capabilities',timeout=5) as response:
                result=json.load(response)
            self.assertEqual(result,server.capability_stats())
        finally:http.shutdown();http.server_close();thread.join()
if __name__=='__main__':unittest.main()
