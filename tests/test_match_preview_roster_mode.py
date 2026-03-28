from __future__ import annotations

from datetime import date
import importlib
import sys
import types


def _load_match_preview_module():
    fake_rankings = types.ModuleType("services.global_t20_rankings")
    fake_rankings.get_batting_rankings_service = lambda *args, **kwargs: {"rankings": []}
    fake_rankings.get_bowling_rankings_service = lambda *args, **kwargs: {"rankings": []}
    sys.modules["services.global_t20_rankings"] = fake_rankings

    import services.match_preview as match_preview_module

    return importlib.reload(match_preview_module)


def _patch_gather_dependencies(match_preview, monkeypatch, capture):
    monkeypatch.setattr(match_preview, "resolve_team_identifier", lambda identifier: identifier)
    monkeypatch.setattr(match_preview, "get_venue_match_stats", lambda **kwargs: {})
    monkeypatch.setattr(match_preview, "get_venue_phase_stats", lambda **kwargs: {})
    monkeypatch.setattr(match_preview, "_get_h2h_last_n", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        match_preview,
        "_get_recent_form",
        lambda *args, **kwargs: {"record": "WWLLL", "wins": 2, "losses": 3},
    )
    monkeypatch.setattr(match_preview, "_get_latest_elo", lambda *args, **kwargs: 1000)
    monkeypatch.setattr(
        match_preview,
        "_get_match_history_bundle",
        lambda *args, **kwargs: {
            "venue_results": [],
            "team1_names": [],
            "team1_results": [],
            "team2_names": [],
            "team2_results": [],
            "h2h_recent": [],
        },
    )
    monkeypatch.setattr(
        match_preview,
        "_summarize_team_recent_matches",
        lambda *args, **kwargs: {
            "record": "WWLLL",
            "wins_batting_first": 1,
            "wins_chasing": 1,
            "sample_size": 2,
            "reached_avg_winning_score_batting_first": 0,
            "chased_avg_chasing_score": 0,
            "batting_first_scores": [],
            "chasing_scores": [],
        },
    )
    monkeypatch.setattr(match_preview, "_summarize_recent_venue_trend", lambda *args, **kwargs: {"sample_size": 0})
    monkeypatch.setattr(match_preview, "_same_country_hint", lambda *args, **kwargs: {})

    def fake_matchup_summary(db, team1, team2, start_date, end_date, use_current_roster=False, **kwargs):
        capture["use_current_roster"] = use_current_roster
        capture["teams"] = (team1, team2)
        return {
            "available": True,
            "lineup_players": {team1: [], team2: []},
            "lineup_sources": {team1: "match_data", team2: "pre_season"},
        }

    monkeypatch.setattr(match_preview, "_summarize_matchups_and_fantasy", fake_matchup_summary)
    monkeypatch.setattr(match_preview, "_summarize_top_ranked_lineup_players", lambda **kwargs: {})
    monkeypatch.setattr(match_preview, "build_phase_wise_strategy_templates", lambda context: {})
    monkeypatch.setattr(match_preview, "_build_story_signals", lambda context: {})


def test_gather_preview_context_sets_use_current_roster_for_ipl_vs_ipl(monkeypatch):
    match_preview = _load_match_preview_module()
    capture = {}
    _patch_gather_dependencies(match_preview, monkeypatch, capture)
    monkeypatch.setattr(match_preview, "_is_ipl_team", lambda team_name: team_name in {"CSK", "MI"})

    context = match_preview.gather_preview_context(
        venue="Wankhede Stadium",
        team1_identifier="CSK",
        team2_identifier="MI",
        db=object(),
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 28),
    )

    assert capture["use_current_roster"] is True
    assert context["lineup_selection"]["use_current_roster"] is True
    assert context["lineup_selection"]["team1_source"] == "match_data"
    assert context["lineup_selection"]["team2_source"] == "pre_season"


def test_gather_preview_context_keeps_recent_mode_for_non_ipl(monkeypatch):
    match_preview = _load_match_preview_module()
    capture = {}
    _patch_gather_dependencies(match_preview, monkeypatch, capture)
    monkeypatch.setattr(match_preview, "_is_ipl_team", lambda team_name: False)

    context = match_preview.gather_preview_context(
        venue="Lord's",
        team1_identifier="England",
        team2_identifier="Australia",
        db=object(),
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 28),
    )

    assert capture["use_current_roster"] is False
    assert context["lineup_selection"]["use_current_roster"] is False
