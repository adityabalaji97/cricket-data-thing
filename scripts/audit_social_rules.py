"""
Audit the Instagram queue against the social rules (services/social_rules.findings; SOCIAL_RULES_ENFORCEMENT_PLAN.md
chunk 0): every rule broken, counted by the builder that made the post and the card visual it's on, with one example
each. The baseline the later chunks are measured against, and (chunk 6) the nightly check.

    python scripts/audit_social_rules.py                     # ready posts
    python scripts/audit_social_rules.py --posted-days 14    # and those posted or planned in the last 14 days
    python scripts/audit_social_rules.py --json              # the same, as JSON (the digest / run summary)

Lint findings come from the slides' data; layout findings (title lines, cut-off labels, legends...) from the last
render (facts.layout, scripts/lib/slide_layout.mjs), so a post rendered before chunk 1 has none until it's re-rendered.

A builder is the post's key family and source ("debate/ig-backlog", "preview/ig-match-day", "otd/hand").
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def builder(angle_key: str, source: str) -> str:
    """'ig:preview-india-west-indies-2026-10-17' + 'ig-match-day' -> 'preview/ig-match-day'."""
    key = (angle_key or "").split(":", 1)[-1]
    return f"{key.split('-', 1)[0] or '?'}/{source or '?'}"


def packs(db, posted_days: int) -> List[Dict[str, Any]]:
    from sqlalchemy import text

    since = date.today() - timedelta(days=posted_days)
    return [dict(r) for r in db.execute(text("""
        SELECT p.id, p.angle_key, p.source, p.status, p.planned_for, p.facts->>'kind' AS kind,
               p.facts->'layout' AS layout, s.data
        FROM content_packs p JOIN chart_snapshots s ON s.id = p.facts->>'carousel_id'
        WHERE p.channel = 'instagram'
          AND (p.status = 'ready' OR (:days > 0 AND p.status = 'posted' AND p.planned_for >= :since))
        ORDER BY p.id
    """), {"days": posted_days, "since": since}).mappings()]


def audit(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """{packs, flagged, rules: [{rule, label, findings, packs, by_builder, by_visual, example}]}, most common first."""
    from services.social_rules import LAYOUT_RULES, RULES, findings

    labels = {**RULES, **LAYOUT_RULES}

    by_rule: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"findings": 0, "packs": set(), "by_builder": Counter(),
                                                              "by_visual": Counter(), "example": None})
    flagged = set()
    for r in rows:
        b = builder(r["angle_key"], r["source"])
        slides = ((r["data"] or {}).get("slides")) or []
        drawn = [{**f, "visual": ((slides[f["slide"] - 1].get("card") or {}).get("visual")
                                  if 0 < f["slide"] <= len(slides) else None)} for f in (r.get("layout") or [])]
        for f in findings(slides, r["kind"]) + drawn:
            agg = by_rule[f["rule"]]
            agg["findings"] += 1
            agg["packs"].add(r["id"])
            agg["by_builder"][b] += 1
            if f.get("visual"):
                agg["by_visual"][f["visual"]] += 1
            agg["example"] = agg["example"] or {"pack": r["angle_key"], "slide": f["slide"], "message": f["message"]}
            flagged.add(r["id"])
    out = [{"rule": k, "label": labels.get(k, k), "findings": v["findings"], "packs": len(v["packs"]),
            "by_builder": dict(v["by_builder"].most_common()), "by_visual": dict(v["by_visual"].most_common()),
            "example": v["example"]} for k, v in by_rule.items()]
    out.sort(key=lambda x: -x["findings"])
    return {"packs": len(rows), "flagged": len(flagged), "rules": out}


def report(result: Dict[str, Any]) -> str:
    lines = [f"{result['packs']} posts checked, {result['flagged']} break at least one rule", ""]
    for r in result["rules"]:
        lines.append(f"{r['findings']:>4}  {r['label']}  ({r['packs']} posts)")
        lines.append("        builders: " + ", ".join(f"{b} {n}" for b, n in r["by_builder"].items()))
        if r["by_visual"]:
            lines.append("        visuals:  " + ", ".join(f"{v} {n}" for v, n in list(r["by_visual"].items())[:6]))
        e = r["example"]
        lines.append(f"        e.g. {e['pack']}" + (f" slide {e['slide']}" if e["slide"] else "") + f": {e['message'][:110]}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--posted-days", type=int, default=0, help="also posts posted in the last N days")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    from database import get_session

    result = audit(packs(next(get_session()), args.posted_days))
    print(json.dumps(result, default=str, indent=1) if args.json else report(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
