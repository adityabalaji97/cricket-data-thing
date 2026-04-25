from services import nl2query


def _mock_llm_response(filters=None, group_by=None, explanation="mock"):
    return {
        "filters": filters or {},
        "group_by": group_by or [],
        "explanation": explanation,
        "confidence": "high",
        "suggestions": [],
    }


def test_century_query_forces_per_innings_batter_grouping(monkeypatch):
    nl2query._cache.clear()
    monkeypatch.setattr(
        nl2query,
        "call_openai",
        lambda _q: _mock_llm_response(
            filters={"batters": ["Virat Kohli"], "query_mode": "delivery"},
            group_by=["batter"],
        ),
    )

    result = nl2query.parse_nl_query("virat kohli 100+ scores")
    assert result["success"] is True
    assert result["filters"]["query_mode"] == "delivery"
    assert result["filters"]["min_runs"] == 100
    assert "match_id" in result["group_by"]
    assert "innings" in result["group_by"]
    assert "batter" in result["group_by"]


def test_venue_phrase_becomes_filter_and_not_unintended_group_by(monkeypatch):
    nl2query._cache.clear()
    monkeypatch.setattr(
        nl2query,
        "call_openai",
        lambda _q: _mock_llm_response(
            filters={},
            group_by=["toss_decision", "match_outcome", "venue"],
        ),
    )

    result = nl2query.parse_nl_query("toss decision vs match outcome at Eden Gardens")
    assert result["success"] is True
    assert result["filters"]["venue"] == "Eden Gardens"
    assert "venue" not in result["group_by"]


def test_since_query_drops_llm_end_date_when_not_explicit(monkeypatch):
    nl2query._cache.clear()
    monkeypatch.setattr(
        nl2query,
        "call_openai",
        lambda _q: _mock_llm_response(
            filters={
                "batting_teams": ["Chennai Super Kings"],
                "start_date": "2018-01-01",
                "end_date": "2023-10-31",
                "query_mode": "delivery",
            },
            group_by=["batting_team", "match_outcome", "innings"],
        ),
    )

    result = nl2query.parse_nl_query("csk in chasing wins since 2018")
    assert result["success"] is True
    assert result["filters"]["start_date"] == "2018-01-01"
    assert "end_date" not in result["filters"]


def test_wicketless_query_maps_to_max_wickets_zero_with_bowler_grouping(monkeypatch):
    nl2query._cache.clear()
    monkeypatch.setattr(
        nl2query,
        "call_openai",
        lambda _q: _mock_llm_response(
            filters={"bowlers": ["Jasprit Bumrah"]},
            group_by=["bowler"],
        ),
    )

    result = nl2query.parse_nl_query("jasprit bumrah wicketless games")
    assert result["success"] is True
    assert result["filters"]["query_mode"] == "delivery"
    assert result["filters"]["max_wickets"] == 0
    assert "match_id" in result["group_by"]
    assert "innings" in result["group_by"]
    assert "bowler" in result["group_by"]


def test_interpretation_fallback_is_populated_from_filters(monkeypatch):
    nl2query._cache.clear()
    monkeypatch.setattr(
        nl2query,
        "call_openai",
        lambda _q: _mock_llm_response(
            filters={
                "batters": ["Virat Kohli"],
                "bowl_kind": ["spin bowler"],
                "query_mode": "delivery",
            },
            group_by=["batter", "phase"],
            explanation="kohli vs spin",
        ),
    )

    result = nl2query.parse_nl_query("kohli vs spin")
    assert result["success"] is True
    assert result["interpretation"]["summary"]
    assert isinstance(result["interpretation"]["suggestions"], list)
    assert any(entity["type"] == "player" for entity in result["interpretation"]["parsed_entities"])


def test_invalid_confidence_defaults_to_medium(monkeypatch):
    nl2query._cache.clear()
    monkeypatch.setattr(
        nl2query,
        "call_openai",
        lambda _q: {
            "filters": {"batters": ["Virat Kohli"], "query_mode": "delivery"},
            "group_by": ["batter"],
            "explanation": "kohli breakdown",
            "confidence": "certain",
            "suggestions": [],
        },
    )

    result = nl2query.parse_nl_query("virat kohli by year")
    assert result["success"] is True
    assert result["confidence"] == "medium"
