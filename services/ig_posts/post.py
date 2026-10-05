"""
A generated question as an Instagram carousel: hook, the lead scatter (the two best angles, the third as brightness),
bars for the other angles, where the overall leader scores (batters), the scorecard with the split verdict, end.

Debate posts stay between 6 and 9 slides; a card the data can't support drops out, and a post with fewer than
MIN_DATA_CARDS data cards isn't made.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.ig_posts import cards as C
from services.ig_posts.planner import scatter_axes

MIN_DATA_CARDS = 3
MAX_BARS = 3


def build(entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """{slides, cards, title, verdict, leaders, players, method} for one generate() entry, or None."""
    q, ctx, chosen = entry["question"], entry["ctx"], entry["plan"]["angles"]
    sample = f"{q.scope_label} · {ctx.n} {('partnerships' if q.role == 'partnership' else q.role + 's')}"
    data_cards: List[Dict[str, Any]] = []
    axes = scatter_axes(chosen)
    used = set()
    if axes:
        x, y, z = axes
        lead = C.scatter(ctx, x, y, sample, z)
        if lead:
            data_cards.append(lead)
            used |= {x.id, y.id}
    for a in [a for a in chosen if a.id not in used][:MAX_BARS]:
        b = C.bars(ctx, a, sample)
        if b:
            data_cards.append(b)
    ranked = ctx.composite(chosen)
    # Where the highlighted player scores (a trending post), else the overall leader.
    top = ctx.subject if ctx.subject and ctx.find(ctx.subject) else (ranked[0]["name"] if ranked else None)
    if top and q.role == "batter":
        z_card = C.zones(ctx, top, q.scope_label)
        if z_card:
            data_cards.append(z_card)
    score = C.scorecard(ctx, chosen, sample)
    if score:
        data_cards.append(score)
    if len(data_cards) < MIN_DATA_CARDS:
        return None
    verdict = (score or {}).get("payload", {}).get("verdict", "")
    slides = ([{"type": "hook", "text": q.text, "kicker": q.kicker, "sub": "Swipe through the data, then have your say"}]
              + [{"type": "card", "card": c, "teams": None} for c in data_cards]
              + [{"type": "end", "heading": "Run it yourself",
                  "body": "Every number comes from ball-by-ball data. Ask your own question on the query builder: it's free."}])
    leaders = sorted({v for v in entry["contest"]["leaders"].values() if v})
    by = entry["plan"]["by"]
    method = (f"{ctx.n} {q.role}s ({q.scope_label}), compared on {', '.join(a.label for a in chosen)}; "
              + ("these measures were picked for this question by our model, Jev." if by == "jev"
                 else "the measures are our default set for this question type."))
    return {"slides": slides, "cards": data_cards, "title": q.text, "verdict": verdict, "leaders": leaders,
            "players": [p for l in leaders for p in l.split(" & ")], "method": method}
