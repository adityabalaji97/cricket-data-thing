"""Replay logged natural-language questions through candidate parser models, side by side.

    python scripts/dev/compare_nl_models.py --limit 100 --out /tmp/nl_compare.json

Takes the most recent distinct questions from nl_query_log (graphic/idea tags stripped, summaries skipped),
parses each one through every config with the same few-shot examples and the full post-processing
(validate_filters, player-name resolution, _post_process_result), and writes every parse, its tokens,
cost and latency to --out. Nothing is written to nl_query_log. Prints a summary against the first config.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sqlalchemy import text  # noqa: E402

from database import SessionLocal  # noqa: E402
from services import nl2query  # noqa: E402

# (label, model, reasoning_effort, service_tier). The first is the baseline the summary compares against.
CONFIG_SETS: Dict[str, List[Tuple[str, str, Optional[str], Optional[str]]]] = {
    "quality": [
        ("gpt-4o", "gpt-4o", None, None),
        ("luna/none", "gpt-6-luna", "none", None),
        ("luna/low", "gpt-6-luna", "low", None),
        ("sol/low", "gpt-6.1-sol", "low", None),
    ],
    "speed": [
        ("luna/low", "gpt-6-luna", "low", None),
        ("luna/low/fast", "gpt-6-luna", "low", "fast"),
        ("5.6luna/low", "gpt-5.6-luna", "low", None),
        ("5.4mini/low", "gpt-5.4-mini", "low", None),
    ],
}
CONFIGS = CONFIG_SETS["quality"]


def questions(db, limit: int) -> List[str]:
    rows = db.execute(text(
        """
        SELECT q FROM (
            SELECT regexp_replace(trim(query_text), '^\\[(graphic|idea)\\] ', '') AS q, max(created_at) AS last
            FROM nl_query_log
            WHERE query_text NOT LIKE :summary AND query_mode IS DISTINCT FROM 'summarize'
            GROUP BY 1
        ) x ORDER BY last DESC
        """
    ), {"summary": "start_date:%"}).fetchall()
    seen, out = set(), []
    for (q,) in rows:
        key = q.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(q.strip())
        if len(out) >= limit:
            break
    return out


def call(question: str, shots, model: str, effort: Optional[str], tier: Optional[str]) -> Dict[str, Any]:
    started = time.monotonic()
    try:
        raw = nl2query.call_openai(question, few_shot_examples=shots, model=model, reasoning_effort=effort,
                                   service_tier=tier)
        return {"raw": raw, "ms": int((time.monotonic() - started) * 1000)}
    except Exception as exc:  # a failed parse is a result too
        return {"error": repr(exc)[:300], "ms": int((time.monotonic() - started) * 1000)}


def finish(question: str, got: Dict[str, Any], db) -> Dict[str, Any]:
    if "error" in got:
        return {"error": got["error"], "ms": got["ms"]}
    raw = dict(got["raw"])
    meta = raw.pop("_meta", None) or {}
    try:
        result = nl2query.validate_filters(raw, query=question)
        for key in ("batters", "bowlers", "players"):
            if isinstance(result["filters"].get(key), list):
                result["filters"][key] = nl2query.resolve_player_names(result["filters"][key], db)
        result = nl2query._post_process_result(question, result)
    except Exception as exc:
        return {"error": f"post-process: {exc!r}"[:300], "ms": got["ms"], **meta}
    filters = {k: v for k, v in (result.get("filters") or {}).items() if k != "query_mode"}
    return {"filters": filters, "group_by": result.get("group_by") or [], "warnings": result.get("warnings") or [],
            "confidence": result.get("confidence"), "ms": got["ms"], **meta}


def same(a: Dict[str, Any], b: Dict[str, Any], key: str) -> bool:
    def norm(v):
        if isinstance(v, dict):
            return {k: norm(x) for k, x in v.items() if x not in (None, [], "")}
        if isinstance(v, list):
            return sorted(json.dumps(norm(x), sort_keys=True) for x in v)
        return v
    return norm(a.get(key)) == norm(b.get(key))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--set", choices=sorted(CONFIG_SETS), default="quality")
    args = ap.parse_args()
    global CONFIGS
    CONFIGS = CONFIG_SETS[args.set]

    db = SessionLocal()
    qs = questions(db, args.limit)
    shots = {q: nl2query.get_few_shot_examples(q, db=db) for q in qs}
    print(f"{len(qs)} questions x {len(CONFIGS)} configs", flush=True)

    jobs = [(q, label, model, effort, tier) for q in qs for label, model, effort, tier in CONFIGS]
    with ThreadPoolExecutor(args.workers) as pool:
        raws = list(pool.map(lambda j: call(j[0], shots[j[0]], j[2], j[3], j[4]), jobs))

    results: Dict[str, Dict[str, Any]] = {q: {} for q in qs}
    for (q, label, _, _, _), got in zip(jobs, raws):
        results[q][label] = finish(q, got, db)
    db.close()
    with open(args.out, "w") as f:
        json.dump(results, f, indent=1, default=str)

    base = CONFIGS[0][0]
    print(f"\n{'config':<14} {'errors':>6} {'filters=':>8} {'group_by=':>9} {'both=':>6} {'avg ms':>7} {'p90 ms':>7} "
          f"{'avg in':>7} {'avg out':>8} {'avg reas':>8} {'$/100 q':>8}")
    for label, *_ in CONFIGS:
        rows = [results[q][label] for q in qs]
        ok = [r for r in rows if "error" not in r]
        pairs = [(results[q][label], results[q][base]) for q in qs
                 if "error" not in results[q][label] and "error" not in results[q][base]]
        f_eq = sum(same(a, b, "filters") for a, b in pairs)
        g_eq = sum(same(a, b, "group_by") for a, b in pairs)
        both = sum(same(a, b, "filters") and same(a, b, "group_by") for a, b in pairs)
        ms = sorted(r["ms"] for r in ok) or [0]
        avg = lambda k: sum((r.get(k) or 0) for r in ok) / max(1, len(ok))  # noqa: E731
        cost = sum((r.get("estimated_cost_usd") or 0) for r in ok) / max(1, len(ok)) * 100
        print(f"{label:<14} {len(rows) - len(ok):>6} {f_eq:>4}/{len(pairs):<3} {g_eq:>5}/{len(pairs):<3} "
              f"{both:>3}/{len(pairs):<3} {sum(ms) / len(ms):>7.0f} {ms[int(len(ms) * 0.9) - 1]:>7} "
              f"{avg('prompt_tokens'):>7.0f} {avg('completion_tokens'):>8.0f} {avg('reasoning_tokens'):>8.0f} "
              f"{cost:>8.3f}")


if __name__ == "__main__":
    main()
