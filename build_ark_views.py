#!/usr/bin/env python3
"""Build deterministic ARK holdings changes and overlap views from stored snapshots."""
from __future__ import annotations

import json
from pathlib import Path

FUNDS = ("ARKK", "ARKQ", "ARKW", "ARKG", "ARKF", "ARKX")


def field(row: dict[str, str], *names: str) -> str:
    for name in names:
        value = row.get(name)
        if value:
            return str(value).strip()
    return ""


def security_key(row: dict[str, str]) -> str:
    return (
        field(row, "cusip", "CUSIP")
        or field(row, "ticker", "Ticker")
        or field(row, "company", "Company", "company_name", "Company Name")
    )


def weight(row: dict[str, str]) -> float | None:
    value = field(row, "weight(%)", "weight (%)", "Weight (%)", "weight", "Weight")
    if not value:
        return None
    try:
        return float(value.replace("%", "").replace(",", ""))
    except ValueError:
        return None


def audit_snapshot(snapshot: dict) -> dict[str, float | int]:
    rows = snapshot["holdings"]
    keys = [security_key(row) for row in rows]
    weights = [weight(row) for row in rows]
    present_keys = [key for key in keys if key]
    present_weights = [value for value in weights if value is not None]
    return {
        "weight_total": round(sum(present_weights), 4),
        "duplicate_identity_count": len(present_keys) - len(set(present_keys)),
        "missing_identity_count": len(keys) - len(present_keys),
        "missing_weight_count": len(weights) - len(present_weights),
    }


def load_history(root: Path) -> list[dict]:
    by_date: dict[str, dict] = {}
    for path in sorted(root.glob("*/*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        dates = {str(s["as_of"]) for s in payload["snapshots"]}
        if len(dates) != 1:
            raise ValueError(f"{path}: inconsistent as-of dates")
        key = next(iter(dates))
        current = by_date.get(key)
        retrieved = max(str(s["retrieved_at"]) for s in payload["snapshots"])
        if current is None or retrieved > current["_retrieved"]:
            payload["_retrieved"] = retrieved
            by_date[key] = payload
    return [by_date[k] for k in sorted(by_date)]


def holdings_by_fund(payload: dict) -> dict[str, dict[str, dict[str, str]]]:
    result = {}
    for snapshot in payload["snapshots"]:
        result[snapshot["fund"]] = {
            security_key(row): row
            for row in snapshot["holdings"]
            if security_key(row)
        }
    return result


def build_changes(previous: dict | None, current: dict) -> dict:
    current_date = current["snapshots"][0]["as_of"]
    result = {"as_of": current_date, "previous_as_of": None, "funds": {}}
    current_funds = holdings_by_fund(current)
    previous_funds = holdings_by_fund(previous) if previous else {}
    if previous:
        result["previous_as_of"] = previous["snapshots"][0]["as_of"]
    for fund in FUNDS:
        old = previous_funds.get(fund, {})
        new = current_funds.get(fund, {})
        additions = sorted(set(new) - set(old))
        removals = sorted(set(old) - set(new))
        changed = []
        for key in sorted(set(old) & set(new)):
            old_weight, new_weight = weight(old[key]), weight(new[key])
            if old_weight != new_weight:
                changed.append(
                    {"security": key, "previous_weight": old_weight, "weight": new_weight}
                )
        result["funds"][fund] = {
            "additions": additions,
            "removals": removals,
            "weight_changes": changed,
        }
    return result


def build_overlap(current: dict) -> dict:
    per_fund = holdings_by_fund(current)
    securities: dict[str, set[str]] = {}
    for fund, rows in per_fund.items():
        for key in rows:
            securities.setdefault(key, set()).add(fund)
    shared = [
        {"security": key, "funds": sorted(funds), "fund_count": len(funds)}
        for key, funds in securities.items()
        if len(funds) > 1
    ]
    shared.sort(key=lambda row: (-row["fund_count"], row["security"]))
    return {"as_of": current["snapshots"][0]["as_of"], "shared_holdings": shared}


def build(root: Path, output_dir: Path) -> None:
    history = load_history(root)
    if not history:
        raise ValueError("no ARK holdings snapshots found")
    output_dir.mkdir(parents=True, exist_ok=True)
    current = history[-1]
    previous = history[-2] if len(history) > 1 else None
    latest = {
        "as_of": current["snapshots"][0]["as_of"],
        "snapshot_count": len(history),
        "funds": {
            item["fund"]: {
                "row_count": item["row_count"],
                "source_csv_url": item["source_csv_url"],
                "source_sha256": item["source_sha256"],
                "audit": audit_snapshot(item),
            }
            for item in current["snapshots"]
        },
    }
    outputs = {
        "latest.json": latest,
        "changes.json": build_changes(previous, current),
        "overlap.json": build_overlap(current),
    }
    for name, payload in outputs.items():
        (output_dir / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=Path("data/ark-holdings"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/ark-views"))
    args = parser.parse_args()
    build(args.input_dir, args.output_dir)


if __name__ == "__main__":
    main()
