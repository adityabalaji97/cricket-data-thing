"""
Everything a preview card may need, fetched once per request and only when a card asks for it.

Every ground card counts the same matches: `innings`, one row per team innings at the ground from
the query builder's team_innings mode, scoped by `scope` (the competitions, in the query builder's
own terms). A card's Data link carries the same scope, so it opens the matches the card counted.
Par comes from the T20 Primer (`match_par`); recent results, head to head and form come from
match history, as on the classic page.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from functools import cached_property
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from urllib.parse import urlencode

WEB_URL = "https://hindsightcricket.com"

#: Columns for the per-innings list (team_innings group_by); the rest come with every row.
INNINGS_GROUP_BY = ["match_id", "innings", "year", "season", "batting_team", "full_length"]


@dataclass
class GroundMatch:
    """One match at the ground, from its two innings rows."""
    id: str
    year: int
    first: Dict[str, Any]
    second: Optional[Dict[str, Any]]

    @property
    def result(self) -> Optional[str]:
        """'bat' (won batting first), 'chase', or None (tie / no result)."""
        if self.first.get("wins"):
            return "bat"
        if self.first.get("losses"):
            return "chase"
        return None

    @property
    def toss_choice(self) -> Optional[str]:
        """What the toss winner chose: 'bat', 'field', or None when unknown."""
        won = self.first.get("pct_batting_side_won_toss")
        return None if won is None else ("bat" if won >= 50 else "field")

    @property
    def full_first(self) -> bool:
        return bool(self.first.get("full_length"))


@dataclass
class PreviewContext:
    db: Any
    venue: str
    team1: str
    team2: str
    fmt: str = "T20"
    gender: str = "male"
    start: Optional[date] = None
    end: Optional[date] = None
    include_international: bool = True
    top_teams: int = 20
    day_or_night: Optional[str] = None
    leagues: List[str] = field(default_factory=list)
    team1_short: Optional[str] = None
    team2_short: Optional[str] = None

    # -- sources ---------------------------------------------------------------------------------

    @cached_property
    def venue_aliases(self) -> List[str]:
        from services.delivery_data_service import get_venue_aliases

        return get_venue_aliases(self.venue)

    @cached_property
    def scope(self) -> Dict[str, Any]:
        """
        The competitions the ground cards count, as query-builder filters.

        The classic venue record reads "no leagues" as every domestic league; the query builder
        reads it as no league at all. So the leagues are listed: the domestic competitions played
        here in the window (or the user's own selection), plus internationals as selected.
        """
        from services.analytics_common import format_filter_sql
        from services.competition_normalizer import international_competitions

        leagues = list(self.leagues)
        if not leagues:
            rows = self.db.execute(text(f"""
                SELECT DISTINCT dd.competition FROM delivery_details dd
                WHERE dd.ground = ANY(:venues) AND {format_filter_sql('dd', self.fmt, self.gender)}
                  AND (CAST(:start AS text) IS NULL OR dd.match_date >= :start)
                  AND (CAST(:end AS text) IS NULL OR dd.match_date <= :end)
                  AND NOT (dd.competition = ANY(:intl))
            """), {"venues": self.venue_aliases, "intl": international_competitions(self.fmt),
                   "start": self.start.isoformat() if self.start else None,
                   "end": self.end.isoformat() if self.end else None}).scalars().all()
            leagues = sorted(r for r in rows if r)
        return {
            "leagues": leagues,
            "include_international": bool(self.include_international),
            "top_teams": self.top_teams if self.include_international else None,
        }

    @cached_property
    def innings(self) -> List[Dict[str, Any]]:
        """Every team innings at the ground in scope (team_innings, grouped by match and innings)."""
        from services.team_innings import query_team_innings

        s = self.scope
        if not s["leagues"] and not s["include_international"]:
            return []  # nothing in scope; an empty filter would mean "everything" to the query builder
        out = query_team_innings(
            self.db, venue=self.venue, start_date=self.start, end_date=self.end, leagues=s["leagues"],
            teams=[], batting_teams=[], bowling_teams=[], innings=None, match_outcome=[], is_chase=None,
            toss_decision=[], day_or_night=self.day_or_night, group_by=INNINGS_GROUP_BY,
            include_international=s["include_international"], top_teams=s["top_teams"], fmt=self.fmt,
            gender=self.gender, match_ids=[], dimension_filters=[], limit=10000, offset=0, ball_level={},
        )
        return out["data"]

    @cached_property
    def ground_matches(self) -> List[GroundMatch]:
        """Matches with a first innings in the data, oldest first."""
        by_match: Dict[str, Dict[int, Dict[str, Any]]] = {}
        for row in self.innings:
            by_match.setdefault(str(row["match_id"]), {})[int(row["innings"])] = row
        out = [GroundMatch(id=mid, year=int(inns[1]["year"]), first=inns[1], second=inns.get(2))
               for mid, inns in by_match.items() if 1 in inns]
        return sorted(out, key=lambda m: (m.year, m.id))

    @cached_property
    def fixture_competition(self) -> Optional[str]:
        """The competition team1 last played in (canonical name): what this fixture most likely is."""
        from services.competition_aliases import canonical_competition

        row = self.db.execute(text("""
            SELECT competition FROM matches
            WHERE (team1 = :team OR team2 = :team) AND format = :fmt AND gender = :gender
              AND (CAST(:end AS date) IS NULL OR date <= :end)
            ORDER BY date DESC LIMIT 1
        """), {"team": self.team1, "fmt": self.fmt, "gender": self.gender, "end": self.end}).scalar()
        return canonical_competition(row) if row else None

    @cached_property
    def primer_par(self) -> Optional[Dict[str, Any]]:
        """
        T20 Primer par by season for this fixture (match_par, nested shrinkage).

        League par is set by competition, season and ground; T20I par by season and country, so
        an international gets the country's par. Men's T20 only; None elsewhere.
        """
        from services.competition_aliases import canonical_competition, canonical_sql, variants_for
        from services.competition_normalizer import international_competitions
        from services.preview_cards.copy import has_primer

        if not has_primer(self.fmt, self.gender) or not self.fixture_competition:
            return None
        intl = international_competitions(self.fmt)
        params = {"venues": self.venue_aliases, "start": self.start, "end": self.end, "intl": intl}
        window = ("(CAST(:start AS date) IS NULL OR m.date >= :start) "
                  "AND (CAST(:end AS date) IS NULL OR m.date <= :end)")
        base = ("FROM matches m JOIN match_par mp ON mp.p_match = m.id AND mp.format = 'T20' "
                "AND mp.gender = 'male' WHERE m.format = 'T20' AND m.gender = 'male' AND " + window)
        if self.fixture_competition in intl:
            country = self.db.execute(text(
                "SELECT country FROM delivery_details WHERE ground = ANY(:venues) AND country IS NOT NULL LIMIT 1"
            ), params).scalar()
            if not country:
                return None
            params["country"] = country
            rows = self.db.execute(text(f"""
                SELECT EXTRACT(YEAR FROM m.date)::int AS year, AVG(mp.par) AS par, COUNT(*) AS n {base}
                  AND mp.par_source = 'international' AND m.competition = ANY(:intl)
                  -- One row per match through the p_match index (~0.2s); delivery_details has no
                  -- country index, so filtering it by country scans the table (~2.5s).
                  AND (SELECT dd.country FROM delivery_details dd WHERE dd.p_match = m.id LIMIT 1) = :country
                GROUP BY 1 ORDER BY 1
            """), params).mappings().all()
            label, where = "T20Is", f"in {country}"
        else:
            # The fixture's competition at this ground; failing that, the ground's main league.
            comp = self.db.execute(text(f"""
                SELECT {canonical_sql('m.competition')} AS comp {base}
                  AND m.venue = ANY(:venues) AND mp.par_source = 'league'
                GROUP BY 1 ORDER BY (({canonical_sql('m.competition')}) = :fixture) DESC, COUNT(*) DESC LIMIT 1
            """), {**params, "fixture": self.fixture_competition}).scalar()
            if not comp:
                return None
            params["variants"] = variants_for(comp) or [comp]
            rows = self.db.execute(text(f"""
                SELECT EXTRACT(YEAR FROM m.date)::int AS year, AVG(mp.par) AS par, COUNT(*) AS n {base}
                  AND m.venue = ANY(:venues) AND mp.par_source = 'league' AND m.competition = ANY(:variants)
                GROUP BY 1 ORDER BY 1
            """), params).mappings().all()
            label, where = canonical_competition(comp), "here"
        series = [{"year": r["year"], "par": round(float(r["par"])), "n": int(r["n"])} for r in rows if r["par"] is not None]
        if not series:
            return None
        return {"competition": label, "where": where, "international": label == "T20Is", "series": series}

    @cached_property
    def venue_record(self) -> Dict[str, Any]:
        import main as app

        return app.get_venue_notes(
            venue=self.venue, start_date=self.start, end_date=self.end, leagues=self.leagues,
            include_international=self.include_international, top_teams=self.top_teams,
            day_or_night=self.day_or_night, format=self.fmt, gender=self.gender, db=self.db,
        ) or {}

    @cached_property
    def history(self) -> Dict[str, Any]:
        import main as app

        return app.get_match_history(
            venue=self.venue, team1=self.team1, team2=self.team2, start_date=self.start, end_date=self.end,
            day_or_night=self.day_or_night, format=self.fmt, gender=self.gender, db=self.db,
        ) or {}

    @cached_property
    def preview(self) -> Dict[str, Any]:
        from routers.match_preview import get_match_preview

        try:
            return get_match_preview(
                venue=self.venue, team1_id=self.team1, team2_id=self.team2, start_date=self.start,
                end_date=self.end, include_international=self.include_international, top_teams=self.top_teams,
                day_or_night=self.day_or_night, format=self.fmt, gender=self.gender, debug=False, db=self.db,
            ) or {}
        except Exception:  # the written preview is best-effort; cards that need it drop out
            return {}

    @property
    def expect(self) -> Dict[str, Any]:
        return self.preview.get("expect") or {}

    # -- labels and links ------------------------------------------------------------------------

    @property
    def t1(self) -> str:
        return self.team1_short or self.team1

    @property
    def t2(self) -> str:
        return self.team2_short or self.team2

    def query_url(self, **params: Any) -> str:
        """A /query link reproducing a card, scoped to this preview's window and format."""
        pairs = []
        scope = {k: v for k, v in self.scope.items() if v}
        base = {"venue": self.venue, "start_date": self.start, "end_date": self.end, **scope, **params}
        for key, value in base.items():
            if value in (None, [], "", False):
                continue
            for v in (value if isinstance(value, list) else [value]):
                text_value = v.isoformat() if isinstance(v, date) else ("true" if v is True else str(v))
                pairs.append((key, text_value))
        pairs.append(("fmt", f"{'mens' if self.gender == 'male' else 'womens'}-{self.fmt.lower()}"))
        return f"{WEB_URL}/query?{urlencode(pairs)}"
