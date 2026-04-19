"""Contract/safety tests for query builder v2 mode + match-context extensions."""


def _assert_not_500(response, label=""):
    assert response.status_code != 500, (
        f"{label} returned 500: {response.text[:300]}"
    )


class TestQueryBuilderV2Contracts:
    def test_invalid_match_outcome_rejected(self, client):
        r = client.get("/query/deliveries?match_outcome=not_a_valid_outcome")
        assert r.status_code == 400
        assert "Invalid match_outcome values" in r.text

    def test_chase_outcome_conflict_rejected(self, client):
        r = client.get("/query/deliveries?is_chase=false&chase_outcome=win")
        assert r.status_code == 400
        assert "chase_outcome cannot be used when is_chase=false" in r.text

    def test_non_delivery_mode_rejects_delivery_only_filters(self, client):
        r = client.get("/query/deliveries?query_mode=batting_stats&line=SHORT")
        assert r.status_code == 400
        assert "Unsupported filters for query_mode=batting_stats" in r.text

    def test_non_bowling_mode_rejects_wicket_threshold_filters(self, client):
        r = client.get("/query/deliveries?query_mode=batting_stats&min_wickets=1")
        assert r.status_code == 400
        assert "Unsupported filters for query_mode=batting_stats" in r.text

    def test_columns_endpoint_still_responds(self, client):
        r = client.get("/query/deliveries/columns")
        _assert_not_500(r, "GET /query/deliveries/columns")
        payload = r.json()
        assert "grouped_filters" in payload["filter_columns"]
        assert "min_wickets" in payload["filter_columns"]["grouped_filters"]
        assert "max_wickets" in payload["filter_columns"]["grouped_filters"]
