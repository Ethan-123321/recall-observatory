import unittest,json
from unittest.mock import patch
import server
class CommandTests(unittest.TestCase):
 def test_undo_offline(self):
  self.assertEqual(server.command('撤销上一步',{})['action'],'undo')
 def test_product_confirmation(self):
  result={'action':'verify','filters':server.DEFAULT,'product':{'query':'玩具','domain':'一般消费品','model':'521','production':'2025-07-05','batch':''},'clarification':''}
  with patch.object(server,'configured',return_value=True),patch.object(server,'qwen',return_value=json.dumps(result)):
   self.assertEqual(server.command('核验我的玩具',{})['product']['model'],'521')
 def test_invalid_model_action(self):
  with patch.object(server,'configured',return_value=True),patch.object(server,'qwen',return_value='{"action":"delete"}'):
   with self.assertRaises(ValueError):server.command('测试',{})
 def test_invalid_product_date(self):
  result={'action':'verify','product':{'production':'2025-02-30'}}
  with patch.object(server,'configured',return_value=True),patch.object(server,'qwen',return_value=json.dumps(result)):
   with self.assertRaises(ValueError):server.command('核验',{})
