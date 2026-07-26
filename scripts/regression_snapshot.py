#!/usr/bin/env python3
"""Golden-response regression harness for the multi-format migration.

The app has no test suite, so this stands in for one: it freezes the JSON responses of a
set of representative men's-T20 endpoints and diffs them after every backend change. The
whole point of Phase 0 is that T20 behaviour stays bit-identical while formats are added,
and this is what proves it.

Typical use:

    # once, against a known-good build
    python scripts/regression_snapshot.py capture

    # after every backend chunk
    python scripts/regression_snapshot.py check

    # regenerate the endpoint list from whatever data the DB actually holds
    python scripts/regression_snapshot.py discover

Notes
-----
* ``discover`` picks sample venues/matches/players straight from the database, ordered
  deterministically, so the generated endpoint list is stable and -- because local is a
  strict subset of production -- valid against both.
* Volatile fields (cache flags, timings, generated prose) are stripped before comparison;
  see ``VOLATILE_KEYS``.
* Goldens live in ``scripts/goldens/`` and are committed. Different environments get
  different subdirectories, because a subset local DB legitimately returns different
  numbers from production.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
GOLDENS_DIR = REPO_ROOT / "scripts" / "goldens"
ENDPOINTS_FILE = GOLDENS_DIR / "endpoints.json"

DEFAULT_BASE_URL = "http://localhost:8000"

# Keys whose values legitimately change between runs and must not fail a diff.
VOLATILE_KEYS = {
    "cached",
    "generated_at",
    "timestamp",
    "elapsed",
    "elapsed_ms",
    "query_time",
    "execution_time_ms",
    "request_id",
    # LLM-generated prose is non-deterministic; the numbers around it are what we guard.
    # The match preview falls back to a deterministic template when the LLM is unavailable,
    # so both the prose and the flags recording which path ran will flip between runs for
    # reasons that have nothing to do with our code. The `sections` block carries the same
    # figures in structured form and stays under test.
    "ai_preview",
    "summary_text",
    "narrative",
    "preview",
    "llm_used",
    "llm_model",
    "llm_strategy",
}


# --------------------------------------------------------------------------------------
# Discovery: build the endpoint list from real data in the DB
# --------------------------------------------------------------------------------------
def discover_endpoints() -> list[dict[str, Any]]:
    """Pick stable sample entities from the DB and build the endpoint list around them."""
    sys.path.insert(0, str(REPO_ROOT))
    from sqlalchemy import text  # noqa: PLC0415

    from database import engine  # noqa: PLC0415

    with engine.connect() as conn:
        # A recent, high-profile IPL match that exists in both local and prod subsets.
        modern_match = conn.execute(
            text(
                """
                SELECT m.id, m.venue, m.team1, m.team2, m.date
                FROM matches m
                WHERE m.competition = 'IPL' AND m.date >= '2024-01-01'
                ORDER BY m.date DESC, m.id
                LIMIT 1
                """
            )
        ).fetchone()

        # A pre-2015 match, to keep the legacy `deliveries` code path under test.
        legacy_match = conn.execute(
            text(
                """
                SELECT m.id, m.venue, m.team1, m.team2, m.date
                FROM matches m
                JOIN deliveries d ON d.match_id = m.id
                WHERE m.date < '2015-01-01'
                GROUP BY m.id, m.venue, m.team1, m.team2, m.date
                ORDER BY m.date DESC, m.id
                LIMIT 1
                """
            )
        ).fetchone()

        # The venue with the most matches -- guarantees a well-populated preview.
        busiest_venue = conn.execute(
            text(
                """
                SELECT venue, count(*) AS n
                FROM matches
                WHERE date >= '2024-01-01'
                GROUP BY venue
                ORDER BY n DESC, venue
                LIMIT 1
                """
            )
        ).fetchone()

        # Two teams that have actually met at that venue.
        preview_pair = conn.execute(
            text(
                """
                SELECT team1, team2
                FROM matches
                WHERE venue = :venue AND date >= '2024-01-01'
                ORDER BY date DESC, id
                LIMIT 1
                """
            ),
            {"venue": busiest_venue.venue if busiest_venue else ""},
        ).fetchone()

        # A high-volume batter, for player-scoped query-builder cases.
        top_batter = conn.execute(
            text(
                """
                -- delivery_details.date is NULL throughout; match_date (varchar, ISO)
                -- is the populated column, so it compares lexicographically.
                SELECT bat AS name, count(*) AS balls
                FROM delivery_details
                WHERE match_date >= '2024-01-01'
                GROUP BY bat
                ORDER BY balls DESC, bat
                LIMIT 1
                """
            )
        ).fetchone()

    if not (modern_match and busiest_venue and preview_pair and top_batter):
        raise SystemExit(
            "discover: the database does not have enough data to build the endpoint list. "
            "Run scripts/dev/setup_local_db.sh first."
        )

    venue = busiest_venue.venue
    batter = top_batter.name

    endpoints: list[dict[str, Any]] = [
        # ---- Query builder (hero 1) -------------------------------------------------
        {
            "name": "qb_columns",
            "path": "/query/deliveries/columns",
            "params": {},
        },
        {
            "name": "qb_basic_group_by_phase",
            "path": "/query/deliveries",
            "params": {
                "start_date": "2024-01-01",
                "leagues": ["IPL"],
                "group_by": ["phase"],
                "limit": 100,
            },
        },
        {
            "name": "qb_batter_vs_pace_by_length",
            "path": "/query/deliveries",
            "params": {
                "batters": [batter],
                "bowl_kind": ["pace bowler"],
                "group_by": ["length"],
                "min_balls": 20,
                "limit": 100,
            },
        },
        {
            "name": "qb_death_overs_venue",
            "path": "/query/deliveries",
            "params": {
                "venue": venue,
                "over_min": 15,
                "over_max": 19,
                "group_by": ["bowl_kind"],
                "limit": 100,
            },
        },
        {
            "name": "qb_chase_outcome",
            "path": "/query/deliveries",
            "params": {
                "start_date": "2024-01-01",
                "leagues": ["IPL"],
                "innings": 2,
                "chase_outcome": ["win"],
                "group_by": ["crease_combo"],
                "limit": 100,
            },
        },
        {
            "name": "qb_batting_stats_mode",
            "path": "/query/deliveries",
            "params": {
                "start_date": "2024-01-01",
                "leagues": ["IPL"],
                "query_mode": "batting_stats",
                "group_by": ["batter"],
                "min_balls": 100,
                "limit": 50,
            },
        },
        {
            "name": "qb_bowling_stats_mode",
            "path": "/query/deliveries",
            "params": {
                "start_date": "2024-01-01",
                "leagues": ["IPL"],
                "query_mode": "bowling_stats",
                "group_by": ["bowler"],
                "min_balls": 100,
                "limit": 50,
            },
        },
        {
            "name": "qb_international",
            "path": "/query/deliveries",
            "params": {
                "start_date": "2024-01-01",
                "include_international": True,
                "top_teams": 10,
                "group_by": ["year"],
                "limit": 100,
            },
        },
        # ---- Scorecard (hero 2) -----------------------------------------------------
        {
            "name": "scorecard_modern",
            "path": f"/matches/{modern_match.id}/scorecard",
            "params": {},
        },
        # ---- Match preview (hero 3) -------------------------------------------------
        {
            "name": "match_preview",
            "path": (
                f"/match-preview/{urllib.parse.quote(venue, safe='')}"
                f"/{urllib.parse.quote(preview_pair.team1, safe='')}"
                f"/{urllib.parse.quote(preview_pair.team2, safe='')}"
            ),
            "params": {"include_international": True, "top_teams": 20},
        },
        # ---- Discovery surfaces the heroes depend on --------------------------------
        {"name": "landing_featured_innings", "path": "/landing/featured-innings", "params": {}},
    ]

    if legacy_match:
        # The pre-2015 path routes to the legacy `deliveries` table -- chunk 0.5 changes
        # exactly this routing, so it needs a golden.
        endpoints.append(
            {
                "name": "scorecard_legacy_pre2015",
                "path": f"/matches/{legacy_match.id}/scorecard",
                "params": {},
            }
        )
        endpoints.append(
            {
                "name": "qb_legacy_pre2015_window",
                "path": "/query/deliveries",
                "params": {
                    "start_date": "2013-01-01",
                    "end_date": "2014-12-31",
                    "group_by": ["phase"],
                    "limit": 100,
                },
            }
        )

    return endpoints


# --------------------------------------------------------------------------------------
# Fetch + normalise
# --------------------------------------------------------------------------------------
def build_url(base_url: str, endpoint: dict[str, Any]) -> str:
    params = endpoint.get("params", {})
    pairs: list[tuple[str, str]] = []
    for key, value in params.items():
        if isinstance(value, list):
            pairs.extend((key, str(item)) for item in value)
        elif isinstance(value, bool):
            pairs.append((key, "true" if value else "false"))
        else:
            pairs.append((key, str(value)))
    query = urllib.parse.urlencode(pairs)
    return f"{base_url.rstrip('/')}{endpoint['path']}" + (f"?{query}" if query else "")


def strip_volatile(value: Any) -> Any:
    """Recursively drop keys whose values are expected to differ between identical runs."""
    if isinstance(value, dict):
        return {k: strip_volatile(v) for k, v in sorted(value.items()) if k not in VOLATILE_KEYS}
    if isinstance(value, list):
        return [strip_volatile(v) for v in value]
    if isinstance(value, float):
        # Guard against float noise from differing aggregation order.
        return round(value, 6)
    return value


def fetch(base_url: str, endpoint: dict[str, Any], timeout: int) -> dict[str, Any]:
    url = build_url(base_url, endpoint)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
        return {"status": response.status, "body": strip_volatile(body)}
    except urllib.error.HTTPError as exc:  # noqa: PERF203
        return {"status": exc.code, "error": exc.read().decode("utf-8")[:2000]}
    except Exception as exc:  # noqa: BLE001
        return {"status": "ERROR", "error": f"{type(exc).__name__}: {exc}"[:2000]}


# --------------------------------------------------------------------------------------
# Diffing
# --------------------------------------------------------------------------------------
def diff_json(expected: Any, actual: Any, path: str = "") -> list[str]:
    """Return human-readable differences, deepest-first, capped by the caller."""
    if type(expected) is not type(actual):
        return [f"{path or '<root>'}: type {type(expected).__name__} -> {type(actual).__name__}"]

    if isinstance(expected, dict):
        diffs = []
        for key in sorted(set(expected) | set(actual)):
            sub = f"{path}.{key}" if path else key
            if key not in expected:
                diffs.append(f"{sub}: added ({json.dumps(actual[key])[:120]})")
            elif key not in actual:
                diffs.append(f"{sub}: removed")
            else:
                diffs.extend(diff_json(expected[key], actual[key], sub))
        return diffs

    if isinstance(expected, list):
        if len(expected) != len(actual):
            return [f"{path or '<root>'}: list length {len(expected)} -> {len(actual)}"]
        diffs = []
        for index, (exp_item, act_item) in enumerate(zip(expected, actual)):
            diffs.extend(diff_json(exp_item, act_item, f"{path}[{index}]"))
        return diffs

    if expected != actual:
        return [f"{path or '<root>'}: {json.dumps(expected)[:80]} -> {json.dumps(actual)[:80]}"]
    return []


# --------------------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------------------
def load_endpoints() -> list[dict[str, Any]]:
    if not ENDPOINTS_FILE.exists():
        raise SystemExit(
            f"{ENDPOINTS_FILE} not found. Run: python scripts/regression_snapshot.py discover"
        )
    return json.loads(ENDPOINTS_FILE.read_text())


def cmd_discover(_args: argparse.Namespace) -> int:
    endpoints = discover_endpoints()
    GOLDENS_DIR.mkdir(parents=True, exist_ok=True)
    ENDPOINTS_FILE.write_text(json.dumps(endpoints, indent=2) + "\n")
    print(f"Wrote {len(endpoints)} endpoints to {ENDPOINTS_FILE.relative_to(REPO_ROOT)}")
    for endpoint in endpoints:
        print(f"  {endpoint['name']:32} {endpoint['path']}")
    return 0


def cmd_capture(args: argparse.Namespace) -> int:
    endpoints = load_endpoints()
    out_dir = GOLDENS_DIR / args.env
    out_dir.mkdir(parents=True, exist_ok=True)

    failures = 0
    for endpoint in endpoints:
        result = fetch(args.base_url, endpoint, args.timeout)
        (out_dir / f"{endpoint['name']}.json").write_text(json.dumps(result, indent=2) + "\n")
        status = result["status"]
        if status != 200:
            failures += 1
            print(f"  !! {endpoint['name']:32} status={status}")
        else:
            size = len(json.dumps(result["body"]))
            print(f"  ok {endpoint['name']:32} {size:>9,} bytes")

    print(f"\nCaptured {len(endpoints)} goldens into {out_dir.relative_to(REPO_ROOT)}")
    if failures:
        print(f"WARNING: {failures} endpoint(s) did not return 200 -- goldens saved anyway.")
        print("Fix those before trusting the baseline.")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    endpoints = load_endpoints()
    golden_dir = GOLDENS_DIR / args.env
    if not golden_dir.exists():
        raise SystemExit(f"No goldens at {golden_dir}. Run capture first.")

    changed = []
    for endpoint in endpoints:
        golden_file = golden_dir / f"{endpoint['name']}.json"
        if not golden_file.exists():
            print(f"  ?? {endpoint['name']:32} no golden (new endpoint)")
            continue

        # Strip volatile keys from the stored golden too, not just the fresh response. Goldens
        # captured before a key was marked volatile still contain it, and without this every
        # addition to VOLATILE_KEYS would force a full re-capture just to clear phantom diffs.
        expected = strip_volatile(json.loads(golden_file.read_text()))
        actual = fetch(args.base_url, endpoint, args.timeout)
        diffs = diff_json(expected, actual)

        if diffs:
            changed.append(endpoint["name"])
            print(f"  XX {endpoint['name']:32} {len(diffs)} difference(s)")
            for line in diffs[: args.max_diffs]:
                print(f"       {line}")
            if len(diffs) > args.max_diffs:
                print(f"       ... and {len(diffs) - args.max_diffs} more")
        else:
            print(f"  ok {endpoint['name']:32} identical")

    print()
    if changed:
        print(f"FAIL: {len(changed)} endpoint(s) changed: {', '.join(changed)}")
        return 1
    print(f"PASS: all {len(endpoints)} endpoints identical to goldens.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--base-url",
        default=os.getenv("HINDSIGHT_BASE_URL", DEFAULT_BASE_URL),
        help=f"API base URL (default {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--env",
        default="local",
        help="Golden subdirectory: 'local' (subset DB) or 'prod'. Default: local",
    )
    parser.add_argument("--timeout", type=int, default=120, help="Per-request timeout, seconds")
    parser.add_argument("--max-diffs", type=int, default=15, help="Diff lines shown per endpoint")

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("discover", help="Rebuild endpoints.json from data in the database")
    sub.add_parser("capture", help="Save current responses as goldens")
    sub.add_parser("check", help="Compare current responses against goldens")

    args = parser.parse_args()
    return {"discover": cmd_discover, "capture": cmd_capture, "check": cmd_check}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
