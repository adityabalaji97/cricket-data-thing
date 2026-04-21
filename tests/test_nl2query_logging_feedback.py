from unittest.mock import MagicMock

from services import nl2query


def _mock_llm_response():
    return {
        "filters": {"batters": ["Virat Kohli"], "query_mode": "delivery"},
        "group_by": ["batter"],
        "explanation": "mock explanation",
        "confidence": "high",
        "suggestions": [],
    }


def test_parse_nl_query_passes_few_shot_examples_to_openai(monkeypatch):
    nl2query._cache.clear()
    expected_examples = [
        {
            "query_text": "kohli vs spin since 2023",
            "parsed_filters": {"batters": ["Virat Kohli"], "bowl_kind": ["spin bowler"], "query_mode": "delivery"},
            "query_mode": "delivery",
            "group_by": ["batter"],
            "explanation": "Example explanation",
            "confidence": "high",
        }
    ]

    captured = {}
    monkeypatch.setattr(nl2query, "get_few_shot_examples", lambda query, db, limit=5: expected_examples)

    def fake_call_openai(query, few_shot_examples=None, model=None):
        captured["query"] = query
        captured["few_shot_examples"] = few_shot_examples
        captured["model"] = model
        return _mock_llm_response()

    monkeypatch.setattr(nl2query, "call_openai", fake_call_openai)

    result = nl2query.parse_nl_query("kohli vs spin", db=object())

    assert result["success"] is True
    assert captured["query"] == "kohli vs spin"
    assert captured["few_shot_examples"] == expected_examples
    assert captured["model"] == nl2query.DEFAULT_NL2QUERY_MODEL


def test_persist_nl_query_log_inserts_and_returns_id():
    mock_db = MagicMock()
    insert_result = MagicMock()
    insert_result.fetchone.return_value = (42,)
    mock_db.execute.return_value = insert_result

    log_id = nl2query.persist_nl_query_log(
        query_text="kohli vs spin",
        parse_result={
            "success": True,
            "filters": {"query_mode": "delivery", "batters": ["Virat Kohli"]},
            "group_by": ["batter"],
            "confidence": "high",
            "explanation": "mock explanation",
        },
        ip_address="127.0.0.1",
        execution_time_ms=123,
        db=mock_db,
    )

    assert log_id == 42
    assert mock_db.commit.called


def test_update_nl_query_feedback_updates_latest_match():
    mock_db = MagicMock()

    select_result = MagicMock()
    select_result.fetchone.return_value = (9,)
    update_result = MagicMock()
    mock_db.execute.side_effect = [select_result, update_result]

    updated = nl2query.update_nl_query_feedback(
        query_text="kohli vs spin",
        feedback="good",
        ip_address="127.0.0.1",
        db=mock_db,
        execution_success=True,
        result_row_count=15,
    )

    assert updated == {"query_log_id": 9, "feedback": "good"}
    assert mock_db.commit.called


def test_update_nl_query_feedback_returns_none_when_no_log_match():
    mock_db = MagicMock()

    first_select = MagicMock()
    first_select.fetchone.return_value = None
    second_select = MagicMock()
    second_select.fetchone.return_value = None
    mock_db.execute.side_effect = [first_select, second_select]

    updated = nl2query.update_nl_query_feedback(
        query_text="unknown query",
        feedback="bad",
        ip_address="127.0.0.1",
        db=mock_db,
    )

    assert updated is None
