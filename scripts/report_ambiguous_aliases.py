#!/usr/bin/env python3
"""List legacy player names that map to more than one full name.

Read-only. These are the names deliberately excluded from canonicalisation
(`services/player_aliases.ALIAS_MAP_CTE`), because collapsing them would risk merging two
different people's careers into one row and presenting it confidently.

Some are harmless spelling variants of one player -- "BG Lister" mapping to both "Benjamin
Lister" and "Ben Lister". Others are genuinely different players who happen to share an
initial-form name: "A Shukla" is both Arpit Shukla and Ayush Shukla. The two cases need
opposite fixes upstream, so the report separates them by whether the first names agree.

    python scripts/report_ambiguous_aliases.py            # summary
    python scripts/report_ambiguous_aliases.py --verbose  # include row counts per name

Fix the variants by collapsing them in `player_aliases`; fix the collisions by giving each
player a distinct legacy name at the source.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from difflib import SequenceMatcher

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text  # noqa: E402

from database import get_database_connection  # noqa: E402


def first_name(full_name: str) -> str:
    return full_name.strip().split(" ")[0].lower() if full_name else ""


def same_person(names: list[str]) -> bool:
    """Whether a set of full names plausibly describes one player.

    Two signals, both about the first name since the last name already matches (the alias
    builder rejects pairs whose last names differ):

    * one first name is a prefix of the other -- "Ben"/"Benjamin", "Brad"/"Bradley";
    * they are near-identical -- "Chamidu"/"Chamindu", which is a transliteration difference,
      not a different player.

    Anything else -- "Arpit"/"Ayush", "Darren"/"Dwayne" -- is treated as two people.
    """
    firsts = sorted({first_name(n) for n in names})
    if len(firsts) < 2:
        return True
    for i, a in enumerate(firsts):
        for b in firsts[i + 1:]:
            if not (a.startswith(b) or b.startswith(a) or SequenceMatcher(None, a, b).ratio() >= 0.85):
                return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--verbose", action="store_true", help="Show stored row counts per name")
    args = parser.parse_args()

    engine, SessionLocal = get_database_connection()
    session = SessionLocal()
    try:
        rows = session.execute(
            text(
                """
                SELECT pa.player_name, pa.alias_name
                FROM player_aliases pa
                JOIN (
                    SELECT player_name
                    FROM player_aliases
                    WHERE player_name IS NOT NULL AND alias_name IS NOT NULL
                    GROUP BY player_name
                    HAVING COUNT(DISTINCT alias_name) > 1
                ) amb ON amb.player_name = pa.player_name
                ORDER BY pa.player_name, pa.alias_name
                """
            )
        ).fetchall()

        grouped = defaultdict(list)
        for legacy, alias in rows:
            grouped[legacy].append(alias)

        collisions, variants = [], []
        for legacy, aliases in sorted(grouped.items()):
            (variants if same_person(aliases) else collisions).append((legacy, aliases))

        counts = {}
        if args.verbose:
            for _, aliases in grouped.items():
                for alias in aliases:
                    counts[alias] = session.execute(
                        text("SELECT count(*) FROM batting_stats WHERE striker = :n"), {"n": alias}
                    ).scalar()

        def show(title, entries, explanation):
            print(f"\n{title} — {len(entries)}")
            print(f"  {explanation}\n")
            for legacy, aliases in entries:
                rendered = []
                for alias in aliases:
                    rendered.append(f"{alias} ({counts[alias]} rows)" if args.verbose else alias)
                print(f"    {legacy:<22} -> {' | '.join(rendered)}")

        print(f"Ambiguous legacy names: {len(grouped)} (all excluded from canonicalisation)")
        show(
            "LIKELY DIFFERENT PLAYERS",
            collisions,
            "First names differ. Merging these would combine two careers — leave them split "
            "and give each a distinct legacy name upstream.",
        )
        show(
            "LIKELY SPELLING VARIANTS",
            variants,
            "Same first name. Safe to collapse in player_aliases, after which they will "
            "canonicalise automatically.",
        )
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
