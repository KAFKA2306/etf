import copy, unittest
from scripts.jpx_listing_brief import build_brief, markdown

BASE={"schema_version":"1.0.0","source_url":"https://www.jpx.co.jp/example","retrieved_at":"2026-01-01T00:00:00+09:00","records":[{"listing_date":"2026-01-01","code":"100A","fund_name":"Alpha Space ETF","index_name":None,"management_company":"A","trading_unit":1,"trust_fee_percent":0.1,"indicative_nav":True,"active_etf":False},{"listing_date":"2026-01-02","code":"200A","fund_name":"Beta ETF","index_name":"Beta","management_company":"B","trading_unit":10,"trust_fee_percent":0.2,"indicative_nav":True,"active_etf":False}]}
WATCH={"schema_version":"1.0.0","id":"all","label":"All","rules":[]}
class TestBrief(unittest.TestCase):
 def test_all_states_and_determinism(self):
  after=copy.deepcopy(BASE); after["retrieved_at"]="2026-02-01T00:00:00+09:00"; after["records"][0]["trust_fee_percent"]=0.11; after["records"].pop(1); after["records"].append({"listing_date":"2026-02-01","code":"300A","fund_name":"Gamma ETF","index_name":None,"management_company":"C","trading_unit":1,"trust_fee_percent":0.3,"indicative_nav":False,"active_etf":True})
  first=build_brief(BASE,after,WATCH); second=build_brief(BASE,after,WATCH)
  self.assertEqual(first,second); self.assertEqual([x["state"] for x in first["items"]],["CHANGED","REMOVED_FROM_CURRENT_SNAPSHOT","ADDED"]); self.assertIn("does not assert delisting",markdown(first))
 def test_watchlist_without_code_change(self):
  watch={"schema_version":"1.0.0","id":"space","rules":[{"field":"fund_name","contains":["Space"]}]}; brief=build_brief(BASE,copy.deepcopy(BASE),watch); self.assertEqual([x["code"] for x in brief["items"]],["100A"])
 def test_missing_is_not_inferred(self):
  broken=copy.deepcopy(BASE); del broken["records"][0]["index_name"]
  with self.assertRaisesRegex(ValueError,"missing index_name"): build_brief(broken,BASE,WATCH)
if __name__=="__main__": unittest.main()
