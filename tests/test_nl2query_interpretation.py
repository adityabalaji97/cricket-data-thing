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
