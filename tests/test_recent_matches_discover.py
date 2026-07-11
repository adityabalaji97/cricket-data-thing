from datetime import date
from types import SimpleNamespace

from services.recent_matches import (
    _canonical_competition_key,
    _competition_values_for_key,
    _date_filter_clause,
    _format_match,
    _score_summaries_for_rows,
    _team_filter_clause,
)


class _MappingResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return self._rows


class _FakeDb:
    def __init__(self, results):
        self._results = list(results)

    def execute(self, *_args, **_kwargs):
        return self._results.pop(0)


def _match_row(**overrides):
    values = {
        "id": "match-1",
        "date": date(2026, 7, 10),
        "venue": "Eden Gardens",
        "team1": "Kolkata Knight Riders",
        "team2": "Chennai Super Kings",
        "winner": "Kolkata Knight Riders",
        "outcome": {"by": {"runs": 17}},
        "competition": "Indian Premier League",
        "match_type": "league",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_format_match_includes_score_summary_fields_and_result_text():
    row = _match_row()
    match = _format_match(
        row,
        score_summary={
            "innings_scores": [
                {"innings": 1, "team": "Kolkata Knight Riders", "runs": 189, "wickets": 4, "balls": 120, "overs": "20.0"},
                {"innings": 2, "team": "Chennai Super Kings", "runs": 172, "wickets": 8, "balls": 120, "overs": "20.0"},
            ],
            "result_text": "KKR won by 17 runs",
        },
    )

    assert match["team1"] == "KKR"
    assert match["innings1_score"] == "189/4 (20.0)"
    assert match["innings2_score"] == "172/8 (20.0)"
    assert match["team1_score"] == "189/4 (20.0)"
    assert match["result_text"] == "KKR won by 17 runs"
    assert match["innings_scores"][0]["runs"] == 189


def test_score_summaries_batch_details_rows_and_derive_wickets_margin():
    row = _match_row(
        id="match-2",
        winner="Chennai Super Kings",
        outcome={},
    )
    db = _FakeDb([
        _MappingResult([
            {
                "match_id": "match-2",
                "innings": 1,
                "batting_team": "Kolkata Knight Riders",
                "bowling_team": "Chennai Super Kings",
                "runs": 155,
                "wickets": 8,
                "legal_balls": 120,
            },
            {
                "match_id": "match-2",
                "innings": 2,
                "batting_team": "Chennai Super Kings",
                "bowling_team": "Kolkata Knight Riders",
                "runs": 156,
                "wickets": 3,
                "legal_balls": 101,
            },
        ]),
    ])

    summaries = _score_summaries_for_rows(db, [row])

    assert summaries["match-2"]["innings_scores"][1]["overs"] == "16.5"
    assert summaries["match-2"]["result_text"] == "CSK won by 7 wickets"


def test_date_filter_window_and_explicit_dates():
    clauses, params = _date_filter_clause("30", None, None)
    assert clauses == ["m.date >= :window_start"]
    assert "window_start" in params

    clauses, params = _date_filter_clause("30", "2026-01-01", "2026-02-01")
    assert clauses == ["m.date >= :date_from", "m.date <= :date_to"]
    assert params["date_from"].isoformat() == "2026-01-01"
    assert params["date_to"].isoformat() == "2026-02-01"


def test_team_filter_matches_full_name_and_abbreviation_candidates():
    clauses, params = _team_filter_clause("KKR")

    assert clauses
    assert "team_candidates" in params
    assert "kkr" in params["team_candidates"]
    assert "kolkata knight riders" in params["team_candidates"]


def test_ipl_competition_aliases_share_one_canonical_key():
    assert _canonical_competition_key("Indian Premier League") == "IPL"
    assert _canonical_competition_key("IPL") == "IPL"
    assert _competition_values_for_key("IPL") == ["IPL", "Indian Premier League"]
    assert _competition_values_for_key("Indian Premier League") == ["IPL", "Indian Premier League"]
