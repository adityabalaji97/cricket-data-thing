"""Unit tests for pure functions in services/match_preview.py."""

import pytest
from services.match_preview import (
    validate_llm_narrative,
    score_preview_lean,
    build_deterministic_preview_sections,
    build_narrative_data_context,
)


# ---------------------------------------------------------------------------
# validate_llm_narrative
# ---------------------------------------------------------------------------

VALID_MARKDOWN = """## Venue Profile
- 20 matches at Test Venue: 12 bat-first wins vs 8 chases.
- Scoring benchmarks: avg winning score 165.

## Form Guide
- Team A WWLWL; batting first scored 170, 155.
- Team B LWWLW; chasing scored 160, 145.

## Head-to-Head
- 5 meetings: Team A 3-2 Team B.
- Most recent went to Team A at Test Venue.

## Key Matchup Factor
- Winning-template pressure point is powerplay (45 runs on average).
- Top picks: Player X (32 exp pts), Player Y (28 exp pts).

## Preview Take
- Slight lean Team A (+4) — recent form, H2H edge.
- Toss could be decisive with chasing edge at this venue.
"""


class TestValidateLlmNarrative:
    def test_valid_markdown_passes(self):
        assert validate_llm_narrative(VALID_MARKDOWN) is True

    def test_wrong_section_count_fails(self):
        # Only 4 sections
        bad = """## Venue Profile
- Bullet one.

## Form Guide
- Bullet one.

## Head-to-Head
- Bullet one.

## Preview Take
- Bullet one.
"""
        assert validate_llm_narrative(bad) is False

    def test_wrong_title_fails(self):
        bad = VALID_MARKDOWN.replace("## Form Guide", "## Recent Form")
        assert validate_llm_narrative(bad) is False

    def test_too_many_bullets_fails(self):
        bad = """## Venue Profile
- One.
- Two.
- Three.
- Four.

## Form Guide
- One.

## Head-to-Head
- One.

## Key Matchup Factor
- One.

## Preview Take
- One.
"""
        assert validate_llm_narrative(bad) is False

    def test_empty_section_fails(self):
        bad = """## Venue Profile

## Form Guide
- One.

## Head-to-Head
- One.

## Key Matchup Factor
- One.

## Preview Take
- One.
"""
        assert validate_llm_narrative(bad) is False


# ---------------------------------------------------------------------------
# score_preview_lean
# ---------------------------------------------------------------------------

def _minimal_context(team1="India", team2="Australia"):
    """Build a minimal context dict with enough structure for score_preview_lean."""
    return {
        "team1": team1,
        "team2": team2,
        "venue": "Test Venue",
        "venue_stats": {
            "total_matches": 20,
            "batting_first_wins": 12,
            "batting_second_wins": 8,
            "average_first_innings": 165,
            "average_second_innings": 155,
            "average_winning_score": 170,
            "average_chasing_score": 160,
            "highest_total": 220,
            "lowest_total": 90,
            "highest_total_chased": 200,
            "lowest_total_defended": 130,
        },
        "phase_stats": {},
        "head_to_head": {"matches": [], "summary": {"sample_size": 0, "team1_wins": 0, "team2_wins": 0}},
        "match_history": {
            "venue_trend": {"sample_size": 0},
            "team1_recent": {"record": "WWLWL", "wins_batting_first": 2, "wins_chasing": 1, "sample_size": 5,
                             "reached_avg_winning_score_batting_first": 1, "chased_avg_chasing_score": 1,
                             "batting_first_scores": [], "chasing_scores": []},
            "team2_recent": {"record": "LWWLW", "wins_batting_first": 1, "wins_chasing": 2, "sample_size": 5,
                             "reached_avg_winning_score_batting_first": 1, "chased_avg_chasing_score": 1,
                             "batting_first_scores": [], "chasing_scores": []},
            "h2h_recent_rows": [],
            "h2h_relevance": {},
        },
        "recent_form": {
            team1: {"record": "WWLWL", "wins": 3, "losses": 2},
            team2: {"record": "LWWLW", "wins": 3, "losses": 2},
        },
        "elo": {team1: 1050, team2: 1030, "delta_team1_minus_team2": 20},
        "screen_story": {
            "match_results_distribution": {
                "venue_toss_signal": {"batting_first_wins": 12, "chasing_wins": 8, "total_matches": 20}
            },
            "innings_scores_analysis": {
                "avg_winning_score_rounded": 170,
                "avg_chasing_score_rounded": 160,
                "highest_total": 220,
                "lowest_total": 90,
                "highest_total_chased": 200,
                "lowest_total_defended": 130,
            },
            "recent_matches_at_venue": {"sample_size": 0},
            "phase_wise_strategy": {},
            "expected_fantasy_points": {"available": False},
            "head_to_head_stats": {"overall_window_summary": {"sample_size": 0, "team1_wins": 0, "team2_wins": 0}, "recent_matches": [], "relevance": {}},
        },
    }


class TestScorePreviewLean:
    def test_returns_expected_keys(self):
        result = score_preview_lean(_minimal_context())
        assert "winner" in result
        assert "score_total" in result
        assert "components" in result
        assert "label" in result
        assert "top_reasons" in result

    def test_no_teams_returns_neutral(self):
        ctx = _minimal_context()
        ctx["team1"] = None
        ctx["team2"] = None
        result = score_preview_lean(ctx)
        assert result["winner"] is None
        assert result["label"] == "Too close to call"

    def test_score_total_is_int(self):
        result = score_preview_lean(_minimal_context())
        assert isinstance(result["score_total"], int)


# ---------------------------------------------------------------------------
# build_deterministic_preview_sections
# ---------------------------------------------------------------------------

class TestBuildDeterministicPreviewSections:
    def test_returns_five_sections(self):
        ctx = _minimal_context()
        sections = build_deterministic_preview_sections(ctx)
        assert len(sections) == 5

    def test_section_titles_match_expected(self):
        ctx = _minimal_context()
        sections = build_deterministic_preview_sections(ctx)
        titles = [s["title"] for s in sections]
        assert titles == ["Venue Profile", "Form Guide", "Head-to-Head", "Key Matchup Factor", "Preview Take"]

    def test_each_section_has_bullets(self):
        ctx = _minimal_context()
        sections = build_deterministic_preview_sections(ctx)
        for s in sections:
            assert len(s["bullets"]) >= 1
            assert len(s["bullets"]) <= 3


# ---------------------------------------------------------------------------
# build_narrative_data_context
# ---------------------------------------------------------------------------

class TestBuildNarrativeDataContext:
    def test_returns_string(self):
        ctx = _minimal_context()
        result = build_narrative_data_context(ctx)
        assert isinstance(result, str)

    def test_contains_expected_sections(self):
        ctx = _minimal_context()
        result = build_narrative_data_context(ctx)
        assert "=== MATCH RESULTS DISTRIBUTION ===" in result
        assert "=== INNINGS SCORES ANALYSIS ===" in result
        assert "=== PHASE-WISE STRATEGY" in result
        assert "=== HEAD-TO-HEAD ===" in result
        assert "=== RECENT MATCHES AT VENUE ===" in result
        assert "=== EXPECTED FANTASY POINTS" in result
        assert "=== PREDICTION SCORING ===" in result

    def test_contains_team_names(self):
        ctx = _minimal_context("India", "Australia")
        result = build_narrative_data_context(ctx)
        assert "India" in result
        assert "Australia" in result
