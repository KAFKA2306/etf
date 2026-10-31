#!/usr/bin/env python3
import argparse, hashlib, json
from pathlib import Path

FIELDS=("listing_date","code","fund_name","index_name","management_company","trading_unit","trust_fee_percent","indicative_nav","active_etf")
STATES=("ADDED","CHANGED","UNCHANGED","REMOVED_FROM_CURRENT_SNAPSHOT")

def load_json(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def manifest_hash(snapshot):
    payload=json.dumps(snapshot,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
    return hashlib.sha256(payload).hexdigest()
def validate_snapshot(snapshot):
    for key in ("schema_version","source_url","retrieved_at","records"):
        if key not in snapshot: raise ValueError(f"snapshot missing {key}")
    seen=set()
    for row in snapshot["records"]:
        missing=[f for f in FIELDS if f not in row]
        if missing: raise ValueError(f"record {row.get('code','?')} missing {','.join(missing)}")
        code=str(row["code"])
        if code in seen: raise ValueError(f"duplicate code {code}")
        seen.add(code)
def diff_snapshots(before,after):
    validate_snapshot(before); validate_snapshot(after)
    old={str(r["code"]):r for r in before["records"]}; new={str(r["code"]):r for r in after["records"]}; out=[]
    for code in sorted(old.keys()|new.keys()):
        if code not in old: state="ADDED"
        elif code not in new: state="REMOVED_FROM_CURRENT_SNAPSHOT"
        else: state="UNCHANGED" if all(old[code][f]==new[code][f] for f in FIELDS) else "CHANGED"
        changes={f:{"before":old.get(code,{}).get(f),"after":new.get(code,{}).get(f)} for f in FIELDS if old.get(code,{}).get(f)!=new.get(code,{}).get(f)}
        out.append({"code":code,"state":state,"record":new.get(code) or old.get(code),"changes":changes})
    return out
def watch_match(item,watch):
    if not watch.get("rules"): return True
    row=item["record"]
    for rule in watch["rules"]:
        value=row.get(rule["field"])
        if value in rule.get("values",[]): return True
        if isinstance(value,str) and any(x.lower() in value.lower() for x in rule.get("contains",[])): return True
    return False
def build_brief(before,after,watch):
    if watch.get("schema_version")!="1.0.0": raise ValueError("unsupported watchlist schema_version")
    items=[x for x in diff_snapshots(before,after) if watch_match(x,watch)]
    return {"schema_version":"1.0.0","watchlist":{"id":watch["id"],"label":watch.get("label",watch["id"])},"provenance":{"before":{"source_url":before["source_url"],"retrieved_at":before["retrieved_at"],"manifest_sha256":manifest_hash(before)},"after":{"source_url":after["source_url"],"retrieved_at":after["retrieved_at"],"manifest_sha256":manifest_hash(after)}},"summary":{s:sum(i["state"]==s for i in items) for s in STATES},"items":items}
def markdown(brief):
    p=brief["provenance"]
    lines=[f'# JPX ETF listing brief: {brief["watchlist"]["label"]}',"",f'Before: {p["before"]["retrieved_at"]} ({p["before"]["manifest_sha256"]})',f'After: {p["after"]["retrieved_at"]} ({p["after"]["manifest_sha256"]})',"","| State | Code | Fund |","|---|---|---|"]
    for x in brief["items"]: lines.append(f'| {x["state"]} | {x["code"]} | {x["record"]["fund_name"]} |')
    lines += ["","Note: REMOVED_FROM_CURRENT_SNAPSHOT means only that the code is absent from the later saved snapshot. It does not assert delisting.","",f'Source: {p["after"]["source_url"]}']
    return "\n".join(lines)+"\n"
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("before"); ap.add_argument("after"); ap.add_argument("--watchlist",required=True); ap.add_argument("--out",required=True); a=ap.parse_args()
    brief=build_brief(load_json(a.before),load_json(a.after),load_json(a.watchlist)); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    (out/"brief.json").write_text(json.dumps(brief,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); (out/"brief.md").write_text(markdown(brief),encoding="utf-8")
if __name__=="__main__": main()
