#!/usr/bin/env python3
"""Build deterministic JPX ETF listing diffs from saved snapshots."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "etf.jpx-listing-brief.v1"
COMPARE_FIELDS = (
    "listing_date",
    "code",
    "fund_name",
    "index_name",
    "management_company",
    "trading_unit",
    "trust_fee_percent",
    "indicative_nav",
    "active_etf",
)
STATUSES = ("ADDED", "CHANGED", "UNCHANGED", "REMOVED_FROM_CURRENT_SNAPSHOT")


def _read_json(path: Path) -> tuple[dict[str, Any], bytes]:
    payload = path.read_bytes()
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value, payload


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _snapshot_provenance(path: Path, manifest_path: Path | None) -> dict[str, Any]:
    snapshot, raw = _read_json(path)
    records = snapshot.get("records")
    if not isinstance(records, list):
        raise ValueError(f"{path} records must be an array")
    manifest_sha256 = None
    if manifest_path is not None:
        _, manifest_raw = _read_json(manifest_path)
        manifest_sha256 = _sha256(manifest_raw)
    return {
        "path": str(path),
        "source_url": snapshot.get("source_url"),
        "retrieved_at": snapshot.get("retrieved_at"),
        "snapshot_sha256": _sha256(raw),
        "manifest_sha256": manifest_sha256,
    }


def _records_by_code(snapshot: dict[str, Any], path: Path) -> dict[str, dict[str, Any]]:
    records = snapshot.get("records")
    if not isinstance(records, list):
        raise ValueError(f"{path} records must be an array")
    result: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("code"), str):
            raise ValueError(f"{path} contains a record without a string code")
        code = record["code"]
        if code in result:
            raise ValueError(f"{path} contains duplicate code {code}")
        result[code] = {field: record.get(field) for field in COMPARE_FIELDS}
    return result


def _status(before: dict[str, Any] | None, after: dict[str, Any] | None) -> tuple[str, list[str]]:
    if before is None:
        return "ADDED", []
    if after is None:
        return "REMOVED_FROM_CURRENT_SNAPSHOT", []
    changed = [field for field in COMPARE_FIELDS if before.get(field) != after.get(field)]
    return ("CHANGED" if changed else "UNCHANGED"), changed


def _matches(record: dict[str, Any], rule: dict[str, Any]) -> bool:
    codes = rule.get("codes", [])
    companies = rule.get("management_companies", [])
    active = rule.get("active_etf")
    if codes and record.get("code") not in codes:
        return False
    if companies and record.get("management_company") not in companies:
        return False
    if active is not None and record.get("active_etf") is not active:
        return False
    return True


def build_brief(
    previous_path: Path,
    current_path: Path,
    watchlist_path: Path,
    watchlist_name: str,
    previous_manifest: Path | None = None,
    current_manifest: Path | None = None,
) -> dict[str, Any]:
    previous, _ = _read_json(previous_path)
    current, _ = _read_json(current_path)
    config, _ = _read_json(watchlist_path)
    if config.get("schema_version") != "etf.jpx-watchlists.v1":
        raise ValueError("unsupported watchlist schema_version")
    watchlists = config.get("watchlists")
    if not isinstance(watchlists, dict) or watchlist_name not in watchlists:
        raise ValueError(f"unknown watchlist: {watchlist_name}")
    rule = watchlists[watchlist_name]
    if not isinstance(rule, dict):
        raise ValueError("watchlist rule must be an object")

    before = _records_by_code(previous, previous_path)
    after = _records_by_code(current, current_path)
    changes = []
    for code in sorted(set(before) | set(after)):
        old = before.get(code)
        new = after.get(code)
        status, changed_fields = _status(old, new)
        visible_record = new if new is not None else old
        assert visible_record is not None
        if not _matches(visible_record, rule):
            continue
        changes.append({
            "code": code,
            "status": status,
            "changed_fields": changed_fields,
            "before": old,
            "after": new,
        })

    counts = {status: sum(change["status"] == status for change in changes) for status in STATUSES}
    return {
        "schema_version": SCHEMA_VERSION,
        "watchlist": {"name": watchlist_name, "config_schema_version": config["schema_version"], "rule": rule},
        "provenance": {
            "previous": _snapshot_provenance(previous_path, previous_manifest),
            "current": _snapshot_provenance(current_path, current_manifest),
        },
        "semantics": {
            "removed_from_current_snapshot": "Record was present in the previous saved snapshot and is absent from the current saved snapshot. This does not assert delisting.",
            "missing_values": "Null or missing source fields remain null; the brief does not infer replacements.",
        },
        "counts": counts,
        "changes": changes,
    }


def render_markdown(brief: dict[str, Any]) -> str:
    p = brief["provenance"]
    lines = [
        f"# JPX ETF listing brief: {brief['watchlist']['name']}",
        "",
        f"Schema: `{brief['schema_version']}`",
        "",
        "## Provenance",
        "",
        f"- Previous source: {p['previous']['source_url']}",
        f"- Previous retrieved_at: {p['previous']['retrieved_at']}",
        f"- Previous snapshot SHA-256: `{p['previous']['snapshot_sha256']}`",
        f"- Previous manifest SHA-256: `{p['previous']['manifest_sha256']}`",
        f"- Current source: {p['current']['source_url']}",
        f"- Current retrieved_at: {p['current']['retrieved_at']}",
        f"- Current snapshot SHA-256: `{p['current']['snapshot_sha256']}`",
        f"- Current manifest SHA-256: `{p['current']['manifest_sha256']}`",
        "",
        "`REMOVED_FROM_CURRENT_SNAPSHOT` means absent from the current saved snapshot only. It does not assert delisting.",
        "",
        "## Changes",
        "",
        "| Status | Code | Fund | Changed fields |",
        "| --- | --- | --- | --- |",
    ]
    for change in brief["changes"]:
        record = change["after"] or change["before"] or {}
        fields = ", ".join(change["changed_fields"]) or "-"
        lines.append(f"| {change['status']} | {change['code']} | {record.get('fund_name') or ''} | {fields} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--previous", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--watchlists", type=Path, required=True)
    parser.add_argument("--watchlist", required=True)
    parser.add_argument("--previous-manifest", type=Path)
    parser.add_argument("--current-manifest", type=Path)
    parser.add_argument("--json-out", type=Path, required=True)
    parser.add_argument("--markdown-out", type=Path, required=True)
    args = parser.parse_args()
    brief = build_brief(args.previous, args.current, args.watchlists, args.watchlist, args.previous_manifest, args.current_manifest)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(brief, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown_out.write_text(render_markdown(brief), encoding="utf-8")


if __name__ == "__main__":
    main()
