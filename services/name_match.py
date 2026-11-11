"""
One of our players for a name spelt another way (an auction list, a news report): "Digvesh Singh Rathi" ->
"Digvesh Rathi", "Philip Salt" -> "Phil Salt", "Ravisrinivasan Sai Kishore" -> "Sai Kishore". Shared by the retention
posts (articles/ipl-retention/post.py) and the auction loader (services/auctions.py).

First the aliases (services/player_aliases), two hops; else everyone sharing his first name or surname. Either way a
match must be the same name spelt another way (every word of the shorter name close to a word of the other: two hops
through initials can reach a different player) and the only one; otherwise None.
"""
from __future__ import annotations

from difflib import SequenceMatcher
from typing import Callable, Optional

from sqlalchemy import text


def same(a: str, b: str) -> bool:
    wa, wb = a.lower().replace("\xa0", " ").split(), b.lower().replace("\xa0", " ").split()
    if not wa or not wb:
        return False
    short_, long_ = (wa, wb) if len(wa) <= len(wb) else (wb, wa)
    return all(max(SequenceMatcher(None, w, x).ratio() for x in long_) >= 0.75 for w in short_)


def match_display_name(db, name: str, accept: Optional[Callable[[str], bool]] = None) -> Optional[str]:
    """Our display name for `name`, or None when no single player fits. `accept`: a further check on each candidate
    (the auction loader keeps players active around the auction's year)."""
    from services.player_aliases import expand_name_group

    name = " ".join(name.replace("\xa0", " ").split())
    if not name:
        return None
    names = set(expand_name_group([name], db))
    names |= set(expand_name_group(sorted(names), db))
    known = db.execute(text("SELECT display_name FROM player_identity WHERE display_name = ANY(:n)"),
                       {"n": sorted(names)}).scalars().all()
    ok = accept or (lambda _k: True)
    if name in known:  # his own name: no further check (a check is for spellings that might be someone else)
        return name
    fits = sorted({k for k in known if same(name, k) and ok(k)})
    if not fits:
        w = name.split()
        pool = db.execute(text("SELECT display_name FROM player_identity WHERE display_name ILIKE :a OR display_name ILIKE :b"),
                          {"a": f"%{w[0]}%", "b": f"%{w[-1]}%"}).scalars().all()
        fits = sorted({k for k in pool if same(name, k) and ok(k)})
    return fits[0] if len(fits) == 1 else None
