"""
A1, "At a glance": the first card, a grid of tiles summarising the story.

Built after every other card, from those cards' own payloads, so a tile can never disagree with
the card it opens. A tile exists only when its card does; tapping it jumps to that card.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from services.preview_cards.copy import short_venue, span
from services.preview_cards.spec import Card, Info

MAX_TILES = 6


def _tiles(ctx, cards: Dict[str, Card]) -> List[dict]:
    tiles = []
    par = cards.get("par")
    if par:
        tiles.append({"card": "par", "label": "Par", "value": str(par.payload["value"]),
                      "sub": par.payload.get("caption") or "first-innings total"})
    res = cards.get("results")
    if res:
        p = res.payload
        tiles.append({"card": "results", "label": "Chasing", "value": f"{p['chase_wins']}/{p['decided']}",
                      "sub": "within noise" if p["within_noise"] else "a real edge"})
    h2h = cards.get("head-to-head")
    if h2h:
        s = h2h.payload["stats"]
        a, b = int(s.get("team1_wins") or 0), int(s.get("team2_wins") or 0)
        lead = ctx.t1 if a > b else ctx.t2 if b > a else None
        tiles.append({"card": "head-to-head", "label": "Head to head",
                      "value": f"{max(a, b)}–{min(a, b)}" if lead else f"{a}–{b}",
                      "sub": f"{lead} lead" if lead else "level", "team": lead})
    form = cards.get("form")
    if form:
        for team, wins, played in zip((ctx.t1, ctx.t2), form.payload["wins"], form.payload["played"]):
            if played:
                tiles.append({"card": "form", "label": f"{team} form", "value": f"{wins}/{played}",
                              "sub": "wins, last 5" if played == 5 else f"wins, last {played}", "team": team})
    quirk = cards.get("boundary-zones") or cards.get("dismissals")
    if quirk and len(tiles) < MAX_TILES:
        if quirk.id == "boundary-zones":
            top = next(z for z in quirk.payload["zones"] if z["zone"] == quirk.payload["top"])
            tiles.append({"card": quirk.id, "label": "Boundaries", "value": f"{top['pct']:.0f}%",
                          "sub": f"to {top['name'].lower()} (usually {top['usual_pct']:.0f}%)"})
        else:
            top = next(r for r in quirk.payload["rows"] if r["kind"] == quirk.payload["top"])
            tiles.append({"card": quirk.id, "label": "Wickets", "value": f"{top['pct']}%",
                          "sub": f"{top['label'].lower()} (usually {top['usual_pct']}%)"})
    if res and len(tiles) < MAX_TILES and res.payload["toss"]["known"]:
        t = res.payload["toss"]
        tiles.append({"card": "results", "label": "Toss winners", "value": f"{round(100 * t['chose_chase'] / t['known'])}%",
                      "sub": "chose to chase"})
    return tiles[:MAX_TILES]


def at_a_glance(ctx, cards: List[Card]) -> Optional[Card]:
    by_id = {c.id: c for c in cards}
    tiles = _tiles(ctx, by_id)
    if len(tiles) < 3:
        return None  # a summary of one or two numbers is just those cards
    bits = []
    if "par" in by_id:
        bits.append(f"par about {by_id['par'].payload['value']}")
    res = by_id.get("results")
    if res:
        p = res.payload
        chase_leads = p["chase_wins"] * 2 >= p["decided"]
        if p["within_noise"]:
            bits.append("no clear edge for chasing" if chase_leads else "no clear edge for batting first")
        else:
            bits.append("chasing sides win more" if chase_leads else "sides batting first win more")
    title = ", ".join(bits).capitalize() if bits else f"{ctx.t1} v {ctx.t2}: the key numbers"
    return Card(
        id="glance", chapter="glance", visual="tiles",
        title=title, help="Tap a number for the full card",
        sample=f"{ctx.t1} v {ctx.t2} at {short_venue(ctx.venue)} · {span(ctx.start, ctx.end)}",
        n=len(tiles), payload={"tiles": tiles},
        info=Info(what="The story's headline numbers in one place. Each tile opens the card it comes from, "
                       "with its sample and method."),
        relevance=100.0,  # always first
    )
