"""
Myth posts: a hypothesis-lab result (analysis/hypotheses/results/<slug>.json) as a carousel of charts.

    hook (the note's question) -> the claim -> the evidence (bucket bars from the result's tables) -> every test as an
    estimate with its 95% interval (forest) -> the verdict, part by part -> end

Each result has its own tables, so each post has a SPEC: which table to draw, which effects to plot and what to call
them in plain words. Every number is the result file's own; titles are written here from those numbers. Only results
whose note is published get a post (an unpublished finding hasn't been reviewed).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from services.ig_posts.cards import card, fmt

RESULTS = Path(__file__).resolve().parents[2] / "analysis" / "hypotheses" / "results"

#: The note title of each result (scripts/notes/build_hypothesis_notes.py META), to find a note's result.
TITLES = {
    "h0-varun-first-over": "Does one bad over break Varun Chakravarthy?",
    "h1-impact-player": "Did the Impact Player rule really inflate IPL scoring?",
    "h2-varun-figured-out": "Have batters figured Varun Chakravarthy out?",
    "h3-iyer-anchor": "Is Shreyas Iyer an anchor, not an accelerator?",
    "h4-india-openers": "Are India's T20I openers all or nothing?",
    "h5-anchor-dead": "Is the T20 anchor dead?",
    "h6-bumrah-death": "Is Jasprit Bumrah the best death bowler in T20?",
    "h7-toss-india": "Does the toss matter at Indian venues?",
    "h8-matchups": "Are bowling matchups overrated?",
}


def _buckets(result, table: str, value: str, n: Optional[str], labels: Dict[str, str]) -> List[Dict[str, Any]]:
    rows = result["tables"][table]
    return [{"label": short, "value": rows[key][value], "n": rows[key].get(n) if n else None}
            for key, short in labels.items() if rows.get(key) and rows[key].get(value) is not None]


def bucket_card(result, cid: str, table: str, value: str, labels: Dict[str, str], metric: str, title: Callable,
                sample: str, n: Optional[str] = None, help_: str = "") -> Optional[Dict[str, Any]]:
    buckets = _buckets(result, table, value, n, labels)
    if len(buckets) < 2:
        return None
    by = {b["label"]: b["value"] for b in buckets}
    return card(cid, "bucket_bars", title(by), {"metric": {"label": metric, "format": "signed2"}, "buckets": buckets},
                sample, help_)


def forest_card(result, picks: List[tuple], title: Callable, sample: str) -> Optional[Dict[str, Any]]:
    """picks: (effect index, plain label). A test is 'clear' when its 95% interval leaves out no effect."""
    effects = []
    for i, label in picks:
        if i >= len(result["effects"]):
            continue
        e = result["effects"][i]
        lo, hi = e["ci"]
        clear = lo > 0 or hi < 0
        effects.append({"label": label, "estimate": round(e["estimate"], 2), "lo": round(lo, 2), "hi": round(hi, 2),
                        "clear": clear, "call": "clear effect" if clear else "no clear effect"})
    if len(effects) < 2:
        return None
    unit = result["effects"][picks[0][0]].get("unit") or ""
    return card("tests", "forest", title(effects), {"effects": effects, "unit": unit}, sample,
                "Each test: the estimated difference, and the range it could plausibly be in")


def _h0(result) -> List[Dict[str, Any]]:
    first = {"0-6": "0–6", "7-9": "7–9", "10+": "10+"}
    sample = "IPL, every season with ball-by-ball win probability · his matches by runs off his first over"
    return [c for c in (
        bucket_card(result, "first-over", "first_over", "mean_raa_per_over_rest", first, "Varun's RAA per over, rest of the match",
                    lambda b: (f"After a 10+ first over, Varun's rest-of-match RAA falls to {fmt(b['10+'], 'signed2')} an over"
                               f" (from {fmt(b['0–6'], 'signed2')})"),
                    sample, n="matches", help_="Runs saved per over after his first, against an average bowler · by runs off his first over"),
        bucket_card(result, "peers", "first_over", "peer_mean_raa_per_over_rest", first, "Five IPL spinners' RAA per over, rest of the match",
                    lambda b: (f"Other spinners {'drop too' if b['10+'] < b['0–6'] else 'hold up'}: "
                               f"{fmt(b['0–6'], 'signed2')} to {fmt(b['10+'], 'signed2')} an over"),
                    "Chahal, Rashid, Kuldeep and two more · the same split", n="peer_matches_with_rest",
                    help_="The same split for five IPL spinners: is a bad first over a Varun problem, or everyone's?"),
        bucket_card(result, "entry", "entry", "mean_raa_per_over",
                    {"powerplay (overs 1-6)": "Powerplay", "middle (overs 7-15)": "Middle"}, "Varun's RAA per over, by when he came on",
                    lambda b: f"Varun is worth more starting in the powerplay ({fmt(b['Powerplay'], 'signed2')}) than the middle ({fmt(b['Middle'], 'signed2')})",
                    "His matches by the over he came on", n="matches"),
        forest_card(result, [(0, "Bad first over hurts his rest of match"), (1, "Same test, five other IPL spinners"),
                             (2, "Hurts Varun more than the others"),
                             (3, "Better entering in the middle overs"), (4, "Hurt by a big over from the other end")],
                    lambda es: (f"{sum(e['clear'] for e in es)} of {len(es)} tests {'finds' if sum(e['clear'] for e in es) == 1 else 'find'} a clear effect" if any(e["clear"] for e in es)
                                else f"None of the {len(es)} tests finds a clear effect"),
                    "Welch t-tests and bootstraps, 95% intervals"),
    ) if c]


SPECS: Dict[str, Callable[[Dict[str, Any]], List[Dict[str, Any]]]] = {"h0-varun-first-over": _h0}


def slug_for_title(title: str) -> Optional[str]:
    return next((s for s, t in TITLES.items() if t == title), None)


def build(note: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """{hook, kicker, slides, title, verdict} for a published note with a SPEC, else None."""
    slug = slug_for_title(note["title"])
    if not slug or slug not in SPECS or note.get("status") != "published":
        return None
    result = json.loads((RESULTS / f"{slug}.json").read_text())
    cards = SPECS[slug](result)
    if len(cards) < 2:
        return None
    parts = "\n".join(f"{k}: {v}" for k, v in (result.get("parts") or {}).items())
    slides = ([{"type": "hook", "text": note["title"], "kicker": "Myth or fact?", "sub": "We tested it on ball-by-ball data"},
               {"type": "text", "heading": "The claim", "body": result["claim"]}]
              + [{"type": "card", "card": c, "teams": None} for c in cards]
              + [{"type": "verdict", "verdict": result["verdict"], "body": parts},
                 {"type": "end", "heading": "Read the full test",
                  "body": "Every threshold was written down before the analysis ran. The full write-up and data are on Hindsight."}])
    verdict = f"Our verdict: {result['verdict']}. " + "; ".join(f"{k.split('. ', 1)[-1]}: {v.lower()}"
                                                              for k, v in (result.get("parts") or {}).items()) + "."
    return {"hook": note["title"], "slides": slides, "title": note["title"], "verdict": verdict, "slug": slug}
