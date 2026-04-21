from services import nl2query


def test_interpretation_fallback_is_populated_from_filters(monkeypatch):
    nl2query._cache.clear()
    monkeypatch.setattr(
        nl2query,
        "call_openai",
        lambda _q: {
            "filters": {
                "batters": ["Virat Kohli"],
                "bowl_kind": ["spin bowler"],
                "query_mode": "delivery",
            },
            "group_by": ["batter", "phase"],
            "explanation": "kohli vs spin",
            "confidence": "high",
            "suggestions": [],
        },
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


def test_recommended_columns_defaults_for_bowling_query(monkeypatch):
    nl2query._cache.clear()
    monkeypatch.setattr(
        nl2query,
        "call_openai",
        lambda _q: {
            "filters": {"bowlers": ["Jasprit Bumrah"], "query_mode": "bowling_stats"},
            "group_by": ["bowler", "competition"],
            "explanation": "bumrah bowling split",
            "confidence": "high",
            "suggestions": [],
        },
    )

    result = nl2query.parse_nl_query("bumrah economy death overs")

    assert result["success"] is True
    assert len(result["recommended_columns"]) >= 4
    assert "economy" in result["recommended_columns"]
    assert "wickets" in result["recommended_columns"]


def test_recommended_columns_are_sanitized_and_deduped(monkeypatch):
    nl2query._cache.clear()
    monkeypatch.setattr(
        nl2query,
        "call_openai",
        lambda _q: {
            "filters": {"batters": ["Virat Kohli"], "query_mode": "delivery"},
            "group_by": ["batter"],
            "explanation": "kohli metrics",
            "confidence": "high",
            "suggestions": [],
            "recommended_columns": ["runs", "foo", "strike_rate", "runs", "dot_percentage"],
        },
    )

    result = nl2query.parse_nl_query("kohli against spin")

    assert result["success"] is True
    assert "foo" not in result["recommended_columns"]
    assert result["recommended_columns"].count("runs") == 1
    assert "strike_rate" in result["recommended_columns"]


def test_recommended_chart_is_sanitized_when_valid(monkeypatch):
    nl2query._cache.clear()
    monkeypatch.setattr(
        nl2query,
        "call_openai",
        lambda _q: {
            "filters": {"batters": ["Virat Kohli"], "query_mode": "delivery"},
            "group_by": ["batter"],
            "explanation": "kohli by batter",
            "confidence": "high",
            "suggestions": [],
            "recommended_columns": ["runs", "strike_rate", "balls"],
            "recommended_chart": {
                "type": "scatter",
                "x_axis": "runs",
                "y_axis": "strike_rate",
                "reason": "Compares output and scoring speed.",
            },
        },
    )

    result = nl2query.parse_nl_query("kohli grouped by batter")

    assert result["success"] is True
    assert result["recommended_chart"]["type"] == "scatter"
    assert result["recommended_chart"]["x_axis"] == "runs"
    assert result["recommended_chart"]["y_axis"] == "strike_rate"


def test_recommended_chart_invalid_type_becomes_none(monkeypatch):
    nl2query._cache.clear()
    monkeypatch.setattr(
        nl2query,
        "call_openai",
        lambda _q: {
            "filters": {"batters": ["Virat Kohli"], "query_mode": "delivery"},
            "group_by": ["batter"],
            "explanation": "kohli grouped by batter",
            "confidence": "high",
            "suggestions": [],
            "recommended_columns": ["runs", "strike_rate", "balls"],
            "recommended_chart": {"type": "heatmap", "x_axis": "runs", "y_axis": "strike_rate"},
        },
    )

    result = nl2query.parse_nl_query("kohli grouped by batter")

    assert result["success"] is True
    assert result["recommended_chart"] is None
