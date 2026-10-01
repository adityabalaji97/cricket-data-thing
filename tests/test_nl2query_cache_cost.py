from services import nl2query


def _fake_openai(calls):
    def fake(_q):
        calls.append(_q)
        return {
            "filters": {"batters": ["Virat Kohli"], "query_mode": "delivery"},
            "group_by": ["batter"],
            "explanation": "kohli",
            "confidence": "high",
            "suggestions": [],
            "_meta": {
                "model_used": "gpt-4o",
                "prompt_tokens": 1200,
                "completion_tokens": 150,
                "estimated_cost_usd": 0.0045,
            },
        }
    return fake


def test_cache_hit_is_logged_at_zero_cost(monkeypatch):
    nl2query._cache.clear()
    calls = []
    monkeypatch.setattr(nl2query, "call_openai", _fake_openai(calls))

    first = nl2query.parse_nl_query("kohli stats")
    second = nl2query.parse_nl_query("kohli stats")

    assert len(calls) == 1
    assert first["_meta"]["estimated_cost_usd"] == 0.0045
    # The repeat made no OpenAI call, so it must not be billed again in nl_query_log.
    assert second["_meta"] == nl2query.CACHE_HIT_META
    assert second["filters"] == first["filters"]


def test_cached_entry_is_isolated_from_caller_mutation(monkeypatch):
    nl2query._cache.clear()
    monkeypatch.setattr(nl2query, "call_openai", _fake_openai([]))

    first = nl2query.parse_nl_query("kohli stats")
    first["filters"]["batters"].append("Rohit Sharma")
    hit = nl2query.parse_nl_query("kohli stats")
    hit["filters"]["batters"].append("MS Dhoni")

    assert nl2query.parse_nl_query("kohli stats")["filters"]["batters"] == ["Virat Kohli"]
