"""
Milestones within reach: career totals in one competition, and the round numbers a player could
pass in the next match ("37 runs from 3,000 IPL runs").

Careers come from batting_stats / bowling_stats, which cover every season (ball-by-ball detail
only starts in 2015). A player's older seasons can be stored under a legacy spelling ("RG Sharma"
before 2024, "Rohit Sharma" after), so every stored spelling is counted (expand_name_group).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Sequence, Tuple

from sqlalchemy import text

from services.player_aliases import expand_name_group

# (stat, step, smallest milestone, how close counts as "within reach" in one match), per format.
RULES = {
    "T20": (("runs", 500, 500, 60), ("wickets", 50, 50, 4), ("sixes", 50, 50, 4), ("matches", 50, 50, 1)),
    "ODI": (("runs", 1000, 1000, 80), ("wickets", 50, 50, 4), ("sixes", 50, 50, 3), ("matches", 50, 50, 1)),
}
UNITS = {"runs": ("run", "runs"), "wickets": ("wicket", "wickets"), "sixes": ("six", "sixes")}


@dataclass
class Milestone:
    player: str
    side: Optional[str]
    stat: str
    total: int
    target: int

    @property
    def gap(self) -> int:
        return self.target - self.total

    def phrase(self, where: str) -> str:
        """'is 37 runs from 3,000 IPL runs' / 'will play a 100th IPL match'."""
        if self.stat == "matches":
            return f"would play a {self.target}th {where} match" if self.gap == 1 else \
                f"is {self.gap} matches from {self.target:,} {where} matches"
        one, many = UNITS[self.stat]
        return f"is {self.gap} {one if self.gap == 1 else many} from {self.target:,} {where} {many}"

    @property
    def score(self) -> float:
        # Bigger milestones and smaller gaps first; a 100th match is notable but less than runs.
        weight = {"runs": 1.0, "wickets": 1.0, "sixes": 0.7, "matches": 0.6}[self.stat]
        return weight * (self.target ** 0.5) / (1 + self.gap / max(1, self.target) * 100)


def careers(db, players: Sequence[str], competitions: Sequence[str], fmt: str, gender: str,
            end: Optional[date]) -> Dict[str, Dict[str, int]]:
    """Career totals in these competitions for each player (keyed by the name asked for)."""
    out: Dict[str, Dict[str, int]] = {}
    for name in players:
        spellings = expand_name_group([name], db) or [name]
        params = {"names": spellings, "comps": list(competitions), "fmt": fmt, "gender": gender, "end": end}
        bat = db.execute(text("""
            SELECT COALESCE(SUM(b.runs), 0) AS runs, COALESCE(SUM(b.sixes), 0) AS sixes,
                   COUNT(DISTINCT b.match_id) AS innings
            FROM batting_stats b JOIN matches m ON m.id = b.match_id
            WHERE b.striker = ANY(:names) AND m.competition = ANY(:comps) AND m.format = :fmt
              AND m.gender = :gender AND (CAST(:end AS date) IS NULL OR m.date <= :end)
        """), params).mappings().first()
        bowl = db.execute(text("""
            SELECT COALESCE(SUM(w.wickets), 0) AS wickets
            FROM bowling_stats w JOIN matches m ON m.id = w.match_id
            WHERE w.bowler = ANY(:names) AND m.competition = ANY(:comps) AND m.format = :fmt
              AND m.gender = :gender AND (CAST(:end AS date) IS NULL OR m.date <= :end)
        """), params).mappings().first()
        played = db.execute(text("""
            SELECT COUNT(DISTINCT match_id) FROM (
                SELECT b.match_id FROM batting_stats b WHERE b.striker = ANY(:names)
                UNION SELECT w.match_id FROM bowling_stats w WHERE w.bowler = ANY(:names)
            ) x JOIN matches m ON m.id = x.match_id
            WHERE m.competition = ANY(:comps) AND m.format = :fmt AND m.gender = :gender
              AND (CAST(:end AS date) IS NULL OR m.date <= :end)
        """), params).scalar()
        out[name] = {"runs": int(bat["runs"]), "sixes": int(bat["sixes"]), "wickets": int(bowl["wickets"]),
                     "matches": int(played or 0)}
    return out


def within_reach(totals: Dict[str, Dict[str, int]], sides: Dict[str, str], fmt: str) -> List[Milestone]:
    """Every milestone a player could pass in the next match, best first."""
    out: List[Milestone] = []
    for player, stats in totals.items():
        for stat, step, smallest, reach in RULES.get(fmt, RULES["T20"]):
            total = stats.get(stat, 0)
            target = max(smallest, (total // step + 1) * step)
            if 0 < target - total <= reach and total > 0:
                out.append(Milestone(player, sides.get(player), stat, total, target))
    return sorted(out, key=lambda m: -m.score)
