"""
The motion Reel planner (MOTION_REEL_PLAN.md M5): a post's cards and its one-line-per-scene script into a reel spec,
every scene and lit item anchored on the words the voice says, ready for reel_timing.place.

    lit_keys(card)                         -> the items a card lights (its highlighted rows, its cases, its best cell)
    card_scene(card, line_no, line)        -> one scene: the card's own visual, its scope, beats on the names the line says
    hero_scene(card, line)                 -> the opening scene from the hook card's highlighted row (name and number at
                                              full size on frame 0), else the card itself
    close_scene(question, send, credit)    -> the closing pick-one: captions off, the one brand mention in the credit
    plan(cards, lines, team, close)        -> the reel spec, anchored (chapters: opening, the cards, the close)

Rules carried from the cards (docs/social_rules.md): one lit item per spoken name; below-par items are never the lit
item on their own (M7's check); boards get the push or pages so they read on a phone; the closing scene's captions are
off. Nothing here calls a model or the database.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence

CREDIT = "hindsightcricket.com · Data: Himanish Ganjoo & TechRadar, Cricsheet"
#: Boards played a page at a time at a readable size (VisualScene pages).
PAGES = {"case_board": {"field": "cases", "size": 1, "zoom": 1.3},
         "gap_fits": {"field": "rows", "size": 1, "count": 1, "zoom": 1.12}}  # the gap the voice names; the rest stay in the carousel
#: Kinds where every lit item is a decision shown with both sides (a negative number may be lit there).
BOTH_SIDES = {"case_board", "keep_try"}


def _norm(w: str) -> str:
    return re.sub(r"[^a-z0-9]", "", w.lower())


def _names(item: Dict[str, Any]) -> List[str]:
    return [str(item[k]) for k in ("name", "label", "short") if item.get(k)]


def lit_keys(card: Dict[str, Any]) -> List[Dict[str, Any]]:
    """[{key, value}] the card lights: highlighted rows (metric_bars, scorecard...), every case of a case_board, the
    best cell of a grid ("<row> · <column>"), the gap rows of a template; in the card's order."""
    p = card.get("payload") or {}
    v = card.get("visual")
    out: List[Dict[str, Any]] = []
    if v == "case_board":
        return [{"key": c["name"], "value": None} for c in p.get("cases", [])]
    if v == "grid_heat" and p.get("rows") and p.get("cols"):
        best = None
        for r in p["rows"]:
            for j, c in enumerate(r.get("cells") or []):
                if isinstance(c, dict) and c.get("value") is not None and (best is None or c["value"] > best[2]):
                    best = (r["name"], p["cols"][j], c["value"])
        return [{"key": f"{best[0]} · {best[1]}", "value": best[2]}] if best else []
    for r in p.get("rows") or []:
        if isinstance(r, dict) and (r.get("highlight") or r.get("status") == "gap") and _names(r):
            out.append({"key": _names(r)[0], "value": r.get("value", r.get("subject"))})
    return out


def _word_index(line: str, key: str) -> Optional[int]:
    """Where in the line the voice says the item: a surname in any part of its key (last part first), else its first
    word, else None."""
    ws = [_norm(w) for w in line.split()]
    parts = [x for x in key.split(" · ") if x.strip()]  # "Opener · R Rickelton", "J Bumrah · Death"
    for cand in [p.split()[-1] for p in reversed(parts)] + [key.split()[0]]:
        n = _norm(cand)
        if n and n in ws:
            return ws.index(n)
    return None


def card_scene(card: Dict[str, Any], line_no: int, line: str, kicker: Optional[str] = None,
               chapter: int = 0) -> Dict[str, Any]:
    """One scene for a card, its line `line_no` in the script: the card's own visual (moving where its kind has motion),
    its scope line, a beat on each lit item the line names (on that word), below-par items left unlit unless the kind
    shows both sides of a decision."""
    v = card.get("visual")
    s: Dict[str, Any] = {"kind": v, "anchor": {"line": line_no}, "chapter": chapter,
                         "kicker": kicker or card.get("kicker") or ((card.get("payload") or {}).get("metric") or {}).get("label")
                         or (card.get("id") or v or "").replace("_", " ").replace("-", " "),
                         "payload": card.get("payload") or {}, "scope": card.get("sample") or ""}
    if card.get("teams"):
        s["teams"] = card["teams"]
    beats = []
    for item in lit_keys(card):
        if v not in BOTH_SIDES and isinstance(item["value"], (int, float)) and item["value"] < 0:
            continue
        j = _word_index(line, item["key"])
        if j is not None:
            beats.append({"key": item["key"], "anchor": {"line": line_no, "word": j}})
        elif v in BOTH_SIDES or not beats:
            beats.append({"key": item["key"], "anchor": {"line": line_no}})
    if beats:
        s["beats"] = beats
    if v in PAGES:
        s["pages"] = dict(PAGES[v])
    return s


def hero_scene(card: Dict[str, Any], line: str, team: Optional[str] = None) -> Dict[str, Any]:
    """The opening scene: the hook card's highlighted row as the hero (name and number at full size on frame 0, the
    number counting), the next row entering as the second player; or the card itself when it has no such row."""
    p = card.get("payload") or {}
    rows = [r for r in p.get("rows") or [] if isinstance(r, dict) and isinstance(r.get("value"), (int, float))]
    lead = next((r for r in rows if r.get("highlight")), None)
    if not lead or lead["value"] < 0:
        return {**card_scene(card, 0, line), "chapter": 0}
    fmt = (p.get("metric") or {}).get("format", "signed1")
    second = next((r for r in rows if r is not lead and r.get("value", 0) > 0), None)
    data: Dict[str, Any] = {"name": lead["name"], "value": lead["value"], "format": fmt, "from": round(lead["value"] * 0.2, 2),
                            "gloss": lead.get("detail"), "scope": card.get("sample")}
    if second:
        j = _word_index(line, second["name"])
        data["second"] = {"name": second["name"], "value": second["value"],
                          "anchor": {"line": 0, "word": j} if j is not None else {"line": 0, "word": min(4, len(line.split()) - 1)}}
    return {"kind": "hero", "chapter": 0, "kicker": (p.get("metric") or {}).get("label") or card.get("kicker") or "",
            "team": team, "data": data}


def close_scene(question: str, lit: str, send: str, credit: Sequence[str], line_no: int, chapter: int,
                options: Sequence[Any] = ("Keep", "Release")) -> Dict[str, Any]:
    """The closing pick-one (decision 3): the question with its lit half, two equal choices, the send line on one line
    (decision 9), the credit with the one brand mention (decision 8); captions off."""
    return {"kind": "pick_one", "anchor": {"line": line_no}, "chapter": chapter, "captions": False,
            "data": {"question": question, "lit": lit, "options": list(options),
                     "send": {"text": send, "anchor": "Send"}, "credit": [*credit, CREDIT]}}


def plan(cards: Sequence[Dict[str, Any]], lines: Sequence[str], team: Optional[str] = None,
         close: Optional[Dict[str, Any]] = None, chapters: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    """The reel spec for a script: lines[0] is the hook over cards[0] (the hero), lines[1..] one per card in turn,
    and, with `close`, a last line for the pick-one ({question, lit, send, credit?, options?}). Chapters: the opening,
    the cards, the close (or `chapters` labels, one per scene group of equal size). Times come from the voice:
    reel_timing.place(spec, timing)."""
    if len(lines) != len(cards) + (1 if close else 0):
        raise ValueError(f"{len(lines)} lines for {len(cards)} cards{' and a close' if close else ''}: one line a scene")
    scenes: List[Dict[str, Any]] = [hero_scene(cards[0], lines[0], team)]
    mid = 1 if len(cards) > 1 else 0
    for i, card in enumerate(cards[1:], start=1):
        scenes.append(card_scene(card, i, lines[i], chapter=mid))
    labels = list(chapters or ["The hook", "The numbers", "Your call"])
    if close:
        last = len(lines) - 1
        scenes.append(close_scene(close["question"], close["lit"], close["send"], close.get("credit") or [],
                                  last, chapter=2 if mid else 1, options=close.get("options") or ("Keep", "Release")))
    used = sorted({s["chapter"] for s in scenes})
    spec = {"team": team, "fps": 30, "scenes": scenes,
            "chapters": [{"label": labels[k] if k < len(labels) else f"Part {k + 1}", "start": 0, "end": 0} for k in used]}
    return spec


# ---- the IPL retention preset (articles/ipl-retention; MOTION_REEL_PLAN.md M5) -------------------------------------

def _card(slides: Dict[str, Any], card_id: str) -> Optional[Dict[str, Any]]:
    return next((s["card"] for s in slides["slides"] if s.get("type") == "card" and s["card"].get("id") == card_id), None)


def _last(name: str) -> str:
    """What the voice calls a player: the surname, or the first name where the surname is common (Arshdeep, not
    Singh; Rohit, not Sharma), as tweets do (squad_view.called)."""
    from services.squad_view import called

    return called(str(name).split(" · ")[-1])


def _same(short: str, full: str) -> bool:
    """A board's short name ("A Singh") and a card's full one ("Arshdeep Singh"): same surname and initial."""
    a, b = str(short).split(), str(full).split()
    return bool(a and b) and a[-1] == b[-1] and a[0][0] == b[0][0]


def _price(text: str) -> str:
    """"₹16.30 crore" -> "16.3" (said "sixteen point three"), "₹1 crore" -> "1"."""
    n = re.sub(r"[^0-9.]", "", text)
    return n.rstrip("0").rstrip(".") if "." in n else n


def _num(v: float, dp: int = 2) -> str:
    return f"{abs(v):.{dp}f}".rstrip("0").rstrip(".") if dp else f"{abs(round(v))}"


#: How the voice says a phase ("Bumrah saves 11 runs every four overs at the death").
PHASE_SAID = {"powerplay": "in the powerplay", "middle": "in the middle overs", "death": "at the death"}


def _say(name: str, fulls: Sequence[str]) -> str:
    """What the voice calls a player, from any form a card gives ("Opener · U Patel", "U Patel", "Urvil Patel"): his
    full name from the post's cards where they carry it (same initial and surname), then squad_view.called (the
    surname, or the first name where the surname is common: Arshdeep, Rohit, Urvil). Never a bare initial: with no full
    name to go on, the surname."""
    from services.squad_view import called

    short = str(name).split(" · ")[-1].strip()
    full = next((f for f in fulls if _same(short, f)), short)
    said = called(full)
    return said if len(said.strip(".")) > 1 else full.split()[-1]


def _wins(v: float) -> str:
    """Wins added as the cards print them, two decimals ("1.00", not "1")."""
    return f"{abs(v):.2f}"


def retention(slides: Dict[str, Any], team: str, place: str, overseas: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    """The motion Reel for a retention post (articles/ipl-retention/<team>/slides.json), planned with a one-line-per-
    scene script written from the cards' own numbers (no model): the squad's best by wins added (the hero; an Indian
    player when one added at least half the leader's wins, as the hook evidence asks, `overseas` naming the overseas
    players), the squad board with the others named, the batting leader, the bowling grid's best cell, the three calls,
    the biggest gap and who's available, then the big name's keep-or-release. A section with nothing above par is left
    out (no-blame). Returns {spec, lines}; time it with reel_timing and place. Numbers are read from the cards."""
    carried, batting, bowling = _card(slides, "carried"), _card(slides, "batting"), _card(slides, "bowling")
    cases, fits = _card(slides, "cases"), _card(slides, "fits")
    rows = sorted((r for r in carried["payload"]["rows"] if isinstance(r.get("value"), (int, float))), key=lambda r: -r["value"])
    fulls = [r["name"] for r in rows] + [c["name"] for c in (cases or {}).get("payload", {}).get("cases", [])]
    abroad = list(overseas or [])
    indian = [r for r in rows if r["value"] > 0 and not any(_same(r["name"], o) or r["name"] == o for o in abroad)]
    a = indian[0] if abroad and indian and indian[0]["value"] >= 0.5 * rows[0]["value"] else rows[0]
    b = next(r for r in rows if r is not a)
    hero = {**carried, "payload": {**carried["payload"], "rows": [{**a, "highlight": True}] +
                                   [{**r, "highlight": False} for r in rows if r is not a]}}
    cards = [hero]
    lines = [f"{_say(a['name'], fulls)} added {_wins(a['value'])} wins since the 2025 auction. "
             f"{_say(b['name'], fulls)}, {_wins(b['value'])}."]
    said_beats: Dict[int, List[Dict[str, str]]] = {}
    board = (slides["slides"][0].get("hero") or {}).get("payload")
    if board:
        others = sorted((p for g in board["groups"] for p in g["players"]
                         if (p.get("value") or 0) > 0.25 and not any(_same(p["name"], x["name"]) for x in (a, b))),
                        key=lambda p: -p["value"])
        cards.append({"id": "board", "visual": "squad_board", "kicker": "The squad · wins added", "payload": board,
                      "sample": carried.get("sample")})
        # the voice names the others (up to three, best first), so the ring has a word to land on for each chip
        named = [{"key": p["name"], "said": _say(p["name"], fulls)} for p in others[:3]]
        said = [n["said"] for n in named]
        listed = (said[0] if len(said) == 1 else ", ".join(said[:-1]) + " and " + said[-1]) if said else ""
        lines.append("Nobody else added more than a quarter of a win." if not others else
                     f"Only one other added more than a quarter of a win: {listed}." if len(others) == 1 else
                     f"Only {len(others)} others added more than a quarter of a win"
                     + (f", led by {listed}." if len(others) > 3 else f": {listed}."))
        said_beats[len(cards) - 1] = named
    lead = next((r for r in (batting or {}).get("payload", {}).get("rows", [])
                 if r.get("highlight") and (r.get("value") or 0) > 0), None)
    if lead:
        cards.append(batting)
        who = _say(lead["name"], fulls)
        lines.append(f"{who} leads the batting, {_num(lead['value'], 0)} runs above par every hundred balls.")
        said_beats[len(cards) - 1] = [{"key": lead["name"], "said": who}]
    best = next(iter(lit_keys(bowling)), None) if bowling else None
    if best and best["value"] > 0:
        who_short, phase = best["key"].split(" · ")
        who = _say(who_short, fulls)
        cards.append(bowling)
        lines.append(f"{who} saves {_num(best['value'], 0)} runs every four overs "
                     f"{PHASE_SAID.get(phase.lower().split()[0], 'in the ' + phase.lower())}.")
        said_beats[len(cards) - 1] = [{"key": best["key"], "said": who}]
    calls = cases["payload"]["cases"]
    cards.append(cases)
    call_said = [{"key": c["name"], "said": _say(c["name"], fulls)} for c in calls[:3]]
    lines.append("Three calls: " + ", ".join(f"{n['said']} at {_price(c['price'])} crore" for n, c in zip(call_said, calls)) + ".")
    said_beats[len(cards) - 1] = call_said
    gap = next((r for r in (fits or {}).get("payload", {}).get("rows", []) if r.get("status") == "gap" and r.get("options")), None)
    if gap:
        cards.append(fits)
        lines.append(f"The biggest gap is {gap['label'].lower()}. {gap['options'][0]['name']} is available.")
    big = calls[0]
    close = {"question": f"{big['name']}, {big['price']}:", "lit": "keep or release?", "options": ["Keep", "Release"],
             "send": f"Send this to a {place} fan", "credit": [cases.get("sample") or ""]}
    lines.append(f"{big['name']}: keep or release? Send this to a {place} fan.")
    spec = plan(cards, lines, team=team, close=close, chapters=["The core", "The squad", "Your call"])
    # each lit item on the word the voice names him with (cards carry short names; the voice says the full one)
    for i, items in said_beats.items():
        ws = [_norm(w) for w in lines[i].split()]
        beats = [{"key": n["key"], "anchor": {"line": i, "word": ws.index(_norm(n["said"]))}}
                 for n in items if _norm(n["said"]) in ws]
        if beats:
            spec["scenes"][i]["beats"] = beats
    return {"spec": spec, "lines": lines}


# ---- the SMAT round-up (SMAT_ROUNDUP_PLAN.md; MOTION_REEL_PLAN.md M8) -----------------------------------------------

def _line_parts(line: str) -> Dict[str, Any]:
    """A card line as a count-up: "135* off 48" -> 135, "*", "off 48 balls"; "4/12 in 3" -> 4, "/12", "in 3 overs"."""
    m = re.match(r"\s*(\d+)(\*)?(?:/(\d+))?\s+(off|in)\s+([\d.]+)", line or "")
    if not m:
        return {"value": None, "done": "", "detail": line}
    n, star, conceded, word, amount = m.groups()
    if conceded:  # a bowling line: wickets count up, the runs and overs follow
        return {"value": int(n), "done": f"/{conceded}", "detail": f"in {amount} overs"}
    return {"value": int(n), "done": "*" if star else "", "detail": f"off {amount} balls"}


def _spoken_line(line: str) -> str:
    """How the voice says a card line: "135* off 48" -> "135 not out, off 48 balls", "4/12 in 3" -> "four for 12"."""
    p = _line_parts(line)
    if p["value"] is None:
        return line
    if p["done"].startswith("/"):
        return f"{p['value']} for {p['done'][1:]}"
    return f"{p['value']}{' not out' if p['done'] == '*' else ''}, {p['detail']}"


def smat_round(rnd: Dict[str, Any], teams: int = 4) -> Dict[str, Any]:
    """The motion Reel for a SMAT round-up (M8), on the same kit: the round's hero card counting up on frame 0, then one
    franchise per beat in its own colour (the glow, the stripe and its chapter segment change with it: the colour change
    is the chapter tick), the best of the players with no IPL side as the held-back payoff, and bid-or-pass on him.
    rnd: {label, date, hero: {name, team, state, value, line}, franchises: [{team, name, value, line}] (each side's
    best, ranked), pool: count with no IPL side, free: {name, state, value, line, tag}}. `teams` franchises after the
    hero's (four in all: the rest are in the deck). Returns {spec, lines}; time with reel_timing and place."""
    from services.squad_view import TEAMS

    hero, free = rnd["hero"], rnd["free"]
    place = lambda code: TEAMS.get(code, {}).get("short", code)  # noqa: E731
    others = [f for f in rnd["franchises"] if f["team"] != hero["team"]][: teams - 1]
    h = _line_parts(hero["line"])
    lines = [f"{hero['name']}: {_spoken_line(hero['line'])}.",
             f"That is {round(hero['value'])} runs more than an average player from the same spots: the most by an IPL player."]
    scenes: List[Dict[str, Any]] = [{
        "kind": "hero_card", "chapter": 0, "team": hero["team"], "kicker": f"{rnd['label']} · {rnd['date']} · the IPL's Indians",
        "data": {"name": hero["name"], "team": hero["team"], "corner": f"{hero['team']} · {hero['state']}", "rank": 1,
                 "from": max(0, (h["value"] or 0) // 3), "value": h["value"], "done": h["done"], "detail": h["detail"],
                 "sub": {"value": hero["value"], "format": "signed1", "label": "runs above par", "anchor": {"line": 1}},
                 "badge": {"text": "The most by any IPL player", "anchor": "the most"}}}]
    chapters = [{"label": hero["team"], "team": hero["team"], "start": 0, "end": 0}]
    for k, f in enumerate(others, start=2):
        from services.squad_view import called

        p = _line_parts(f["line"])
        lines.append(f"{called(f['name'])} for {place(f['team'])}: {_spoken_line(f['line'])}.")
        scenes.append({"kind": "hero_card", "anchor": {"line": k}, "chapter": len(chapters), "team": f["team"],
                       "kicker": f"{place(f['team'])}'s best · runs above par",
                       "data": {"name": f["name"], "team": f["team"], "corner": f["team"], "rank": None,
                                "from": max(0, (p["value"] or 0) // 3), "value": p["value"], "done": p["done"],
                                "detail": p["detail"],
                                "sub": {"value": f["value"], "format": "signed1", "label": "runs above par",
                                        "anchor": {"line": k, "word": 2}}}})
        chapters.append({"label": f["team"], "team": f["team"], "start": 0, "end": 0})
    k = len(lines)
    fp = _line_parts(free["line"])
    lines.append(f"But {rnd['pool']} played with no IPL side. The best: {free['name']}, {_spoken_line(free['line'])}.")
    last = len(chapters) - 1
    scenes.append({"kind": "pool_count", "anchor": {"line": k}, "chapter": last, "kicker": f"{rnd['label']} · no IPL side",
                   "data": {"count": rnd["pool"], "label": "played with no IPL side",
                            "card": {"name": free["name"], "corner": free["state"], "from": max(0, (fp["value"] or 0) // 3),
                                     "value": fp["value"], "done": fp["done"], "detail": fp["detail"],
                                     "line": f"+{free['value']:.1f} runs above par", "tag": free.get("tag", ""),
                                     "anchor": free["name"].split()[0]}}})
    lines.append(f"{free['name']}: bid or pass? Send this to your team's fans.")
    scenes.append({"kind": "pick_one", "anchor": {"line": k + 1}, "chapter": last, "captions": False,
                   "kicker": "IPL auction · 16 December",
                   "data": {"question": f"{free['name']}:", "lit": "bid or pass?", "options": ["Bid", "Pass"],
                            "sub": "Comment one word.", "send": {"text": "Send this to your team's fans", "anchor": "Send"},
                            "credit": [f"Runs above par, bat + ball · one game · {rnd['label']}, {rnd['date']}", CREDIT]}})
    return {"spec": {"team": hero["team"], "fps": 30, "scenes": scenes, "chapters": chapters}, "lines": lines}
