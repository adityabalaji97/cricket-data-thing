"""
Play-along posts: "Whose innings is this?" from the Guess the Innings game (services/daily_games).

    hook -> the innings (the game's own clue card and wagon wheel) -> clue: season and team -> clue: opposition and
    venue -> clue: initials -> the answer -> end (play the daily game)

The puzzle is an old daily one (PUZZLE_LAG days before the post), so the post never gives away a puzzle people are
still playing on the site.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from services.ig_posts.cards import card

PUZZLE_LAG = 14


def guess_innings_post(db: Session, day: date) -> Optional[Dict[str, Any]]:
    from services import daily_games as dg

    puzzle_day = day - timedelta(days=PUZZLE_LAG)
    p = dg.Puzzle("guess-innings", puzzle_day.isoformat())
    pick = dg.innings_puzzle(db, p)
    if not pick:
        return None
    q = dg.innings_question(pick)
    hint = lambda key: dg.innings_hint(pick, key)  # noqa: E731
    sixes = f", {q['sixes']} six{'es' if q['sixes'] != 1 else ''}" if q.get("sixes") else ""
    innings = card("innings", "innings_wagon", f"{q['runs']} off {q['balls']}{sixes}, from a {q['bat_hand'].split('-')[0].lower()}-hander",
                   {k: q[k] for k in ("runs", "balls", "strike_rate", "fours", "sixes", "bat_hand", "season", "deliveries") if k in q},
                   f"{q['season']} · scoring shots by direction", "Each line is a scoring shot")
    answer = pick["batter"]
    slides = [
        {"type": "hook", "text": "Whose innings is this?", "kicker": f"Play along · {q['season']}",
         "sub": "A clue on every swipe. Guess in the comments before the last slide."},
        {"type": "card", "card": innings, "teams": None},
        {"type": "text", "heading": "Clue 1", "body": f"{q['season']}\n{hint('team')}"},
        {"type": "text", "heading": "Clue 2", "body": f"{hint('opposition')}\nat {hint('venue')}"},
        {"type": "text", "heading": "Clue 3", "body": f"Initials: {hint('initials')}"},
        {"type": "text", "heading": "The answer", "body": f"{answer}\n{q['runs']} off {q['balls']}, {hint('opposition')}\nHow many clues did you need?"},
        {"type": "end", "heading": "Play the daily game",
         "body": "A new innings to guess every day, plus Higher or Lower and Call It: hindsightcricket.com/games"},
    ]
    return {"hook": "Whose innings is this?", "kicker": f"Play along · {q['season']}", "slides": slides,
            "title": f"Whose innings is this? ({q['season']})", "answer": answer, "puzzle": puzzle_day.isoformat()}
