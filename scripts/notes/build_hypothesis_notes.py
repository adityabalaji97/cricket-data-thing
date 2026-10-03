#!/usr/bin/env python3
"""
Turn analysis/hypotheses/results/*.json into /notes drafts and share cards.

Two steps, so the database the numbers come from and the database the drafts go to can differ
(the analysis copy vs the site's):

    # 1. On the analysis database: freeze every chart's data, write the note markdown, card specs
    #    and PNG cards into analysis/hypotheses/notes/<slug>/ for review in git.
    DATABASE_URL=postgresql://localhost:5432/hindsight_analysis \
        python scripts/notes/build_hypothesis_notes.py prepare [h0 h1 ...]

    # 2. Against the site's database: insert the frozen charts as snapshots and the notes as
    #    DRAFTS (never published). Re-running updates the same drafts.
    DATABASE_URL=<site database> python scripts/notes/build_hypothesis_notes.py load [h0 ...]

Charts are stored as static snapshots (kind 'ranking', rendered by the same /embed query view), so
a note shows exactly the numbers the analysis produced. Every chart also gets a 'Reproduce this'
link to the live query builder.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QUERY_CACHE", "0")
os.environ.setdefault("USAGE_LOGGING", "0")

from analysis.hypotheses import credits  # noqa: E402

RESULTS = Path(os.getenv("HYPOTHESIS_RESULTS_DIR") or ROOT / "analysis" / "hypotheses" / "results")
NOTES = Path(os.getenv("HYPOTHESIS_NOTES_DIR") or ROOT / "analysis" / "hypotheses" / "notes")
PREREG = ROOT / "analysis" / "hypotheses" / "preregistration"
REPO_URL = "https://github.com/adityabalaji97/cricket-data-thing/blob/main/analysis/hypotheses/preregistration"
CREATED_BY = "hypothesis-lab"

# Titles are questions: they must not presume the verdict.
META = {
    "h0-varun-first-over": ("Does one bad over break Varun Chakravarthy?", "h0_varun_first_over.md"),
    "h1-impact-player": ("Did the Impact Player rule really inflate IPL scoring?", "h1_impact_player.md"),
    "h2-varun-figured-out": ("Have batters figured Varun Chakravarthy out?", "h2_varun_figured_out.md"),
    "h3-iyer-anchor": ("Is Shreyas Iyer an anchor, not an accelerator?", "h3_iyer_anchor.md"),
    "h4-india-openers": ("Are India's T20I openers all or nothing?", "h4_india_openers.md"),
    "h5-anchor-dead": ("Is the T20 anchor dead?", "h5_anchor_dead.md"),
    "h6-bumrah-death": ("Is Jasprit Bumrah the best death bowler in T20?", "h6_bumrah_death.md"),
    "h7-toss-india": ("Does the toss matter at Indian venues?", "h7_toss_india.md"),
    "h8-matchups": ("Are bowling matchups overrated?", "h8_matchups.md"),
}
VERDICT_COLOUR = {"Supported": "lime", "Not supported": "red", "Partly": "amber", "Inconclusive": "grey"}


def _num(x: Any, digits: int = 2, signed: bool = True) -> str:
    if x is None:
        return "n/a"
    return f"{x:+.{digits}f}" if signed else f"{x:.{digits}f}"


def _ci(effect: Dict[str, Any], digits: int = 2) -> str:
    lo, hi = effect.get("ci") or [None, None]
    return "n/a" if lo is None else f"{_num(lo, digits)} to {_num(hi, digits)}"


def _p(effect: Dict[str, Any]) -> str:
    p = effect.get("p_value")
    return "n/a" if p is None else ("< 0.01" if p < 0.01 else f"{p:.2f}")


def _digits(effect: Dict[str, Any]) -> int:
    unit = (effect.get("unit") or "").lower()
    return 3 if "wpa" in unit or "waa" in unit else 1 if ("100" in unit or "percent" in unit or "rate" in unit) else 2


def _prereg_body(filename: str) -> str:
    text = (PREREG / filename).read_text()
    # Drop the title and the "Common claim" paragraph (the note states the claim already); nest the
    # pre-registration's own headings under "How we tested it".
    paragraphs = text.split("\n\n")[1:]
    paragraphs = [p for p in paragraphs if not p.startswith("Common claim")]
    return re.sub(r"^## ", "### ", "\n\n".join(paragraphs), flags=re.M).strip()


def _small_sample_lines(result: Dict[str, Any]) -> List[str]:
    out = []
    for chart in result["charts"]:
        if chart.get("small_samples"):
            out.append(f"{chart['caption']}: small samples (under 15) in {', '.join(chart['small_samples'])}.")
    return out


def _samples_lines(samples: Dict[str, Any]) -> List[str]:
    lines = []
    for k, v in samples.items():
        if isinstance(v, dict):
            v = ", ".join(f"{kk}: {vv}" for kk, vv in v.items())
        lines.append(f"{k.replace('_', ' ')}: {v}")
    return lines


BLANK_KEYS = (None, "", "-")


def _tidy_chart(data: Dict[str, Any], title: str) -> str:
    """Drop rows whose group value is unrecorded (no previous over, length not logged, unknown
    hand) and flag every bucket under 15 innings on the chart title itself."""
    group_by = data.get("group_by") or []
    kept = [r for r in data.get("rows") or [] if not any(r.get(g) in BLANK_KEYS for g in group_by)]
    dropped = len(data.get("rows") or []) - len(kept)
    data["rows"] = kept
    if "small sample" not in title:
        thin = [f"{' / '.join(str(r.get(g)) for g in group_by)} ({r['innings_count']})"
                for r in kept if isinstance(r.get("innings_count"), (int, float)) and r["innings_count"] < 15]
        if thin:
            more = f" +{len(thin) - 4} more" if len(thin) > 4 else ""
            title += " · small sample (<15 innings): " + ", ".join(thin[:4]) + more
    if dropped:
        title += " · unrecorded values left out"
    data["title"] = title
    return title


def note_markdown(result: Dict[str, Any], chart_titles: Dict[str, str] | None = None) -> str:
    title, prereg = META[result["slug"]]
    chart_titles = chart_titles or {}
    effects = result["effects"]
    tests = sorted({e["test"] for e in effects if e.get("test")})
    parts = [f"*{result['headline']}*", "", "## The claim", "", result["claim"], "",
             "## How we tested it", "",
             "The definitions, thresholds and minimum samples below were written down and committed before the "
             f"analysis was run ([pre-registration]({REPO_URL}/{prereg})).", "",
             _prereg_body(prereg), "", "## What the numbers say", ""]
    for chart in result["charts"][:4]:
        parts += [f"**{chart['caption']}**", "", "{{chart:" + chart["key"] + "}}", ""]
    parts += ["| Effect | Estimate | 95% CI | p | Test | n |", "|---|---|---|---|---|---|"]
    for e in effects:
        d = _digits(e)
        n = ", ".join(f"{k}: {v}" for k, v in (e.get("n") or {}).items())
        parts.append(f"| {e['name']} ({e['unit']}) | {_num(e['estimate'], d)} | {_ci(e, d)} | {_p(e)} | {e['test']} | {n} |")
    parts += ["", f"## Verdict: {result['verdict']}", ""]
    if result.get("parts"):
        parts += [f"- {k}: **{v}**" for k, v in result["parts"].items()] + [""]
    parts += ["Verdicts are applied mechanically from the pre-registered rules: *Supported* when the 95% CI excludes "
              "zero in the claimed direction; *Not supported* when it excludes zero the other way or rules out an "
              "effect of meaningful size; *Inconclusive* otherwise or when a minimum sample is not met.", "",
              "## Caveats and sample sizes", ""]
    parts += [f"- {c}" for c in result.get("caveats", [])]
    parts += [f"- {l}" for l in _samples_lines(result.get("samples", {}))]
    flagged = [t for t in chart_titles.values() if "small sample" in t]
    parts += [f"- {t.replace(' · small sample', ': small sample')}" for t in flagged] or [f"- {l}" for l in _small_sample_lines(result)]
    parts += [f"- Data through {result['data_through']}.", "", "## Reproduce this", ""]
    parts += [f"- [{c['caption']}]({c['url']})" for c in result["charts"]]
    parts += ["- Code: `analysis/hypotheses` in the Hindsight repository.", "", credits.credits_block(", ".join(tests))]
    return "\n".join(parts) + "\n"


# Readable labels for effect details on the cards.
_LABEL_WORDS = [("treated_post", "IPL 2023-26"), ("treated_pre", "IPL 2020-22"),
                ("control_post", "BBL/PSL/CPL 2023-26"), ("control_pre", "BBL/PSL/CPL 2020-22"),
                ("mean_", "average, "), ("_", " ")]


def _label(key: str) -> str:
    for old, new in _LABEL_WORDS:
        key = key.replace(old, new)
    return key


def card_specs(result: Dict[str, Any]) -> Dict[str, Any]:
    """Two or three 1080x1350 cards: claim -> verdict, the headline number, the comparison."""
    title, _ = META[result["slug"]]
    effects = result["effects"]
    primary = effects[0]
    d = _digits(primary)
    claim = result["claim"].replace("A common claim is that ", "").rstrip(".")
    claim = claim[:1].upper() + claim[1:] + "."
    # On a multi-part hypothesis the headline number belongs to the first part: show that part's
    # verdict next to it, not the overall one.
    parts = list((result.get("parts") or {}).items())
    number_verdict, number_label = (parts[0][1], f"VERDICT · {parts[0][0].split('.')[0]}") if parts else (result["verdict"], "VERDICT")

    def rows(effect, digits):
        return [{"label": _label(k), "value": _num(v, digits)} for k, v in (effect.get("detail") or {}).items()
                if isinstance(v, (int, float)) and k not in ("t",)][:5]

    cards = [{
        "kind": "claim", "kicker": f"HYPOTHESIS LAB · {result['hypothesis']}", "eyebrow": "A common claim",
        "title": claim,
        "verdict": result["verdict"], "verdict_colour": VERDICT_COLOUR.get(result["verdict"].split(" (")[0], "grey"),
        "parts": [{"label": k, "value": v} for k, v in (result.get("parts") or {}).items()],
        "headline": result["headline"],
    }, {
        "kind": "number", "kicker": f"HYPOTHESIS LAB · {result['hypothesis']}", "eyebrow": title,
        "stat": _num(primary["estimate"], d), "stat_label": f"{primary['name']} ({primary['unit']})",
        "sub": f"95% CI {_ci(primary, d)} · p {_p(primary)}",
        "rows": rows(primary, d),
        "verdict": number_verdict, "verdict_label": number_label,
        "verdict_colour": VERDICT_COLOUR.get(number_verdict.split(" (")[0].split(" —")[0], "grey"),
    }]
    if len(effects) > 1 and effects[1].get("estimate") is not None:
        e = effects[1]
        dd = _digits(e)
        cards.append({
            "kind": "number", "kicker": f"HYPOTHESIS LAB · {result['hypothesis']}", "eyebrow": "The comparison",
            "stat": _num(e["estimate"], dd), "stat_label": f"{e['name']} ({e['unit']})",
            "sub": f"95% CI {_ci(e, dd)} · p {_p(e)}",
            "rows": rows(e, dd),
        })
    return {"slug": result["slug"], "footer": credits.CARD_FOOTER, "credits": credits.CARD_CREDITS, "cards": cards}


def _selected(keys: List[str]) -> List[Path]:
    files = sorted(RESULTS.glob("*.json"))
    if keys:
        files = [f for f in files if any(f.name.startswith(k.lower() + "-") for k in keys)]
    return files


def prepare(keys: List[str]) -> None:
    from analysis.hypotheses.common import read_only_session
    from services.snapshots import _clean_query_params, _query_data

    for path in _selected(keys):
        result = json.loads(path.read_text())
        out = NOTES / result["slug"]
        out.mkdir(parents=True, exist_ok=True)
        charts = {}
        with read_only_session() as db:
            for chart in result["charts"][:4]:
                params = {k: v for k, v in chart["params"].items()}
                for k in ("start_date", "end_date"):
                    if isinstance(params.get(k), str):
                        params[k] = date.fromisoformat(params[k])
                presentation = dict(chart.get("presentation") or {})
                presentation["title"] = chart["title"]
                data = _query_data(db, _clean_query_params({**params, **presentation}))
                data["hindsight_url"] = chart["url"]
                title = _tidy_chart(data, chart["title"])
                charts[chart["key"]] = {"title": title, "data": data, "params": chart["params"]}
        (out / "charts.json").write_text(json.dumps(charts, indent=1, default=str))
        (out / "note.md").write_text(note_markdown(result, {k: v["title"] for k, v in charts.items()}))
        (out / "cards.json").write_text(json.dumps(card_specs(result), indent=1))
        subprocess.run(["node", str(ROOT / "scripts" / "notes" / "render_cards.mjs"), str(out)], check=True)
        print(f"prepared {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")


def load(keys: List[str]) -> None:
    from sqlalchemy import text

    from database import SessionLocal
    from services import notes as notes_svc
    from services.snapshots import create_static_snapshot

    db = SessionLocal()
    try:
        for path in _selected(keys):
            result = json.loads(path.read_text())
            out = NOTES / result["slug"]
            charts = json.loads((out / "charts.json").read_text())
            body = (out / "note.md").read_text()
            for key, chart in charts.items():
                snap = create_static_snapshot(db, "ranking", chart["data"], chart["title"],
                                              {"hypothesis": result["slug"], "chart": key, "data_through": result["data_through"]},
                                              CREATED_BY)
                body = body.replace("{{chart:" + key + "}}", notes_svc.chart_fence(snap["id"]))
            leftover = re.findall(r"\{\{chart:[^}]+\}\}", body)
            if leftover:
                raise SystemExit(f"{result['slug']}: charts missing for {leftover}")
            title, _ = META[result["slug"]]
            slug = f"hypothesis-{result['slug']}"
            existing = db.execute(text("SELECT id, status FROM notes WHERE slug = :s"), {"s": slug}).first()
            if existing and existing[1] != "draft":
                print(f"skip {slug}: already {existing[1]}")
                continue
            if existing:
                notes_svc.update_note(db, existing[0], {"title": title, "slug": slug, "body_md": body, "dek": result["headline"]})
                print(f"updated draft {slug} (id {existing[0]})")
            else:
                note = notes_svc.create_note(db, title=title, author_id=notes_svc.owner_author_id(db), body_md=body,
                                             dek=result["headline"], kind="analysis", slug=slug)
                print(f"created draft {slug} (id {note['id']})")
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("step", choices=["prepare", "load"])
    parser.add_argument("hypotheses", nargs="*", help="e.g. h0 h6 (default: all results)")
    args = parser.parse_args()
    (prepare if args.step == "prepare" else load)(args.hypotheses)
    return 0


if __name__ == "__main__":
    sys.exit(main())
