from routers import nl2query as nl2query_router


def test_feedback_endpoint_success(client, monkeypatch):
    monkeypatch.setattr(
        nl2query_router,
        "update_nl_query_feedback",
        lambda **kwargs: {"query_log_id": 17, "feedback": "good"},
    )

    response = client.post(
        "/nl2query/feedback",
        json={
            "query_text": "kohli vs spin in death overs",
            "feedback": "good",
            "execution_success": True,
            "result_row_count": 12,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["query_log_id"] == 17
    assert payload["feedback"] == "good"


def test_feedback_endpoint_requires_refined_text_for_refined_feedback(client):
    response = client.post(
        "/nl2query/feedback",
        json={
            "query_text": "kohli vs spin in death overs",
            "feedback": "refined",
        },
    )

    assert response.status_code == 400
    assert "refined_query_text is required" in response.json()["detail"]


def test_feedback_endpoint_returns_404_when_log_not_found(client, monkeypatch):
    monkeypatch.setattr(nl2query_router, "update_nl_query_feedback", lambda **kwargs: None)

    response = client.post(
        "/nl2query/feedback",
        json={
            "query_text": "missing query",
            "feedback": "bad",
        },
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
