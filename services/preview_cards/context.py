"""
Everything a preview card may need, fetched once per request and only when a card asks for it.

The sources are the endpoints the classic preview already calls (venue record, match history,
match preview with its `expect` block), called as functions in-process, so the story and the
classic page always show the same numbers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from functools import cached_property
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

WEB_URL = "https://hindsightcricket.com"


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
        base = {"venue": self.venue, "start_date": self.start, "end_date": self.end, **params}
        for key, value in base.items():
            if value in (None, [], ""):
                continue
            for v in (value if isinstance(value, list) else [value]):
                pairs.append((key, v.isoformat() if isinstance(v, date) else str(v)))
        pairs.append(("fmt", f"{'mens' if self.gender == 'male' else 'womens'}-{self.fmt.lower()}"))
        return f"{WEB_URL}/query?{urlencode(pairs)}"
