#!/usr/bin/env python3
"""Show ElevenLabs usage/status without exposing secrets."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from audio_ad_generate_elevenlabs_dialogue import load_env_files


ROOT = Path(__file__).resolve().parents[1]
ENV_PATHS = (
    ROOT / "local" / "audio-assets" / ".env",
    ROOT / "local" / "elevenlabs" / ".env",
)
LOCAL_META_GLOBS = (
    ROOT / "data" / "processed" / "audio-ads",
)


def main() -> int:
    args = parse_args()
    load_env_files(ENV_PATHS)
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise SystemExit("missing ELEVENLABS_API_KEY in local/audio-assets/.env or shell environment")

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=args.days)

    print("ElevenLabs Status")
    print(f"Checked: {now.isoformat(timespec='seconds')}")
    print()

    subscription = get_json(api_key, "GET", "https://api.elevenlabs.io/v1/user/subscription")
    print_subscription(subscription)
    print()

    character_stats = get_character_stats(api_key, start, now)
    print_character_stats(character_stats)
    print()

    workspace_usage = get_workspace_usage(api_key, start, now)
    print_workspace_usage(workspace_usage)
    print()

    print_local_metadata_summary()
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=14, help="Usage window to fetch, in days.")
    return parser.parse_args()


def get_json(api_key: str, method: str, url: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        return {"_error": {"status": error.code, "detail": detail}}


def get_character_stats(api_key: str, start: datetime, end: datetime) -> dict[str, Any]:
    params = urllib.parse.urlencode(
        {
            "start_unix": int(start.timestamp() * 1000),
            "end_unix": int(end.timestamp() * 1000),
            "aggregation_interval": "day",
        }
    )
    return get_json(api_key, "GET", f"https://api.elevenlabs.io/v1/usage/character-stats?{params}")


def get_workspace_usage(api_key: str, start: datetime, end: datetime) -> dict[str, Any]:
    return get_json(
        api_key,
        "POST",
        "https://api.elevenlabs.io/v1/workspace/analytics/query/usage-by-product-over-time",
        {
            "start_time": int(start.timestamp() * 1000),
            "end_time": int(end.timestamp() * 1000),
            "interval_seconds": 86400,
        },
    )


def print_subscription(data: dict[str, Any]) -> None:
    print("Subscription")
    if data.get("_error"):
        print_error(data["_error"])
        print("Need API key permission: user_read")
        print("Without that, I can show usage history but not tier, limit, remaining characters, or reset date.")
        return

    tier = data.get("tier", "unknown")
    status = data.get("status", "unknown")
    used = data.get("character_count")
    limit = data.get("character_limit")
    reset = data.get("next_character_count_reset_unix")
    print(f"Tier: {tier}")
    print(f"Status: {status}")
    if isinstance(used, int) and isinstance(limit, int):
        remaining = max(0, limit - used)
        pct = (used / limit * 100) if limit else 0
        print(f"Characters: {used:,} used / {limit:,} limit ({remaining:,} remaining, {pct:.1f}% used)")
    if isinstance(reset, int):
        print(f"Next reset: {datetime.fromtimestamp(reset, tz=timezone.utc).isoformat(timespec='seconds')}")
    if data.get("current_overage"):
        overage = data["current_overage"]
        print(f"Current overage: {overage.get('amount')} {overage.get('currency')}")


def print_character_stats(data: dict[str, Any]) -> None:
    print("Character Usage")
    if data.get("_error"):
        print_error(data["_error"])
        return
    values = (data.get("usage") or {}).get("All") or []
    total = sum(float(value or 0) for value in values)
    print(f"Window total: {total:,.0f} characters")
    print_nonzero_daily(data.get("time") or [], values)


def print_workspace_usage(data: dict[str, Any]) -> None:
    print("Workspace Usage")
    if data.get("_error"):
        print_error(data["_error"])
        return
    columns = data.get("columns") or []
    rows = data.get("rows") or []
    indexes = {name: idx for idx, name in enumerate(columns)}
    total_usage = sum_number(rows, indexes.get("total_usage"))
    total_cost = sum_number(rows, indexes.get("total_cost"))
    usage_count = sum_number(rows, indexes.get("usage_count"))
    print(f"Window total usage: {total_usage:,.0f}")
    print(f"Window estimated cost/credits: {total_cost:,.4f}")
    print(f"Requests: {usage_count:,.0f}")
    timestamp_idx = indexes.get("timestamp")
    usage_idx = indexes.get("total_usage")
    cost_idx = indexes.get("total_cost")
    if timestamp_idx is not None and usage_idx is not None:
        for row in rows:
            usage = number_at(row, usage_idx)
            if usage <= 0:
                continue
            cost = number_at(row, cost_idx) if cost_idx is not None else 0
            print(f"- {row[timestamp_idx]}: {usage:,.0f} usage, {cost:,.4f} cost/credits")


def print_local_metadata_summary() -> None:
    print("Local Generated Asset Metadata")
    files = []
    for base in LOCAL_META_GLOBS:
        if base.exists():
            files.extend(base.rglob("*.json"))
    generated = []
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("provider") != "elevenlabs":
            continue
        headers = data.get("responseHeaders") or (data.get("responseMeta") or {}).get("headers") or {}
        generated.append((path, data, headers))
    print(f"ElevenLabs metadata files: {len(generated)}")
    header_chars = 0
    for _, _, headers in generated:
        try:
            header_chars += int(headers.get("character-cost") or headers.get("x-character-count") or 0)
        except (TypeError, ValueError):
            pass
    if header_chars:
        print(f"Header character/cost total: {header_chars:,}")


def print_error(error: dict[str, Any]) -> None:
    detail = str(error.get("detail", "")).replace("\n", " ")
    print(f"Unavailable: HTTP {error.get('status')} {detail}")


def print_nonzero_daily(times: list[Any], values: list[Any]) -> None:
    for stamp, value in zip(times, values):
        amount = float(value or 0)
        if amount <= 0:
            continue
        when = datetime.fromtimestamp(int(stamp) / 1000, tz=timezone.utc).date()
        print(f"- {when}: {amount:,.0f} characters")


def sum_number(rows: list[list[Any]], index: int | None) -> float:
    if index is None:
        return 0.0
    return sum(number_at(row, index) for row in rows)


def number_at(row: list[Any], index: int) -> float:
    try:
        return float(row[index] or 0)
    except (IndexError, TypeError, ValueError):
        return 0.0


if __name__ == "__main__":
    raise SystemExit(main())
