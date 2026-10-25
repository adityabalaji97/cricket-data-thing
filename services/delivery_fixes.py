"""
Corrections the ball-by-ball feed needs on every load, applied straight after the rows land (before stats are built
from them). Each returns the matches it touched, so a caller can rebuild their stats and Primer metrics.

    byes_on_noballs(conn) -> [p_match, ...]

A no-ball that also went for byes or leg-byes: the feed stores the ball's runs as the no-ball alone and the batter's
as the ball's runs minus every extra, so a no-ball + 4 byes reads score 1, batruns -4 (the batter loses the byes and
the ball loses them too). A batter scores nothing off byes or leg-byes: batruns 0, the ball's runs its extras.
Migration 035 fixed the 365 such balls already loaded (2016-2026).
"""
from __future__ import annotations

from typing import List

from sqlalchemy import text

BYES_ON_NOBALLS = """
    UPDATE delivery_details
    SET batruns = 0,
        score = COALESCE(noball, 0) + COALESCE(wide, 0) + COALESCE(byes, 0) + COALESCE(legbyes, 0)
    WHERE batruns < 0
    RETURNING p_match
"""


def byes_on_noballs(conn) -> List[str]:
    return sorted({r[0] for r in conn.execute(text(BYES_ON_NOBALLS))})
