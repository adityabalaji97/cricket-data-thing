"""Contract/safety tests for query builder v2 mode + match-context extensions."""


def _assert_not_500(response, label=""):
    assert response.status_code != 500, (
        f"{label} returned 500: {response.text[:300]}"
    )


class _FakeExecuteResult:
    def __init__(self, rows=None, one=None):
        self._rows = rows if rows is not None else []
        self._one = one

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._one


class _SqlCaptureDb:
    def __init__(self):
        self.statements = []

    def execute(self, statement, _params):
        self.statements.append(str(statement))
        # 1st call: combined query (return empty rows to force fallback path)
        if len(self.statements) == 1:
            return _FakeExecuteResult(rows=[])
        # 2nd call: fallback totals query
        return _FakeExecuteResult(one=(0, 0, 0))


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

    def test_columns_endpoint_exposes_new_group_by_columns(self, client):
        r = client.get("/query/deliveries/columns")
        payload = r.json()
        group_by_cols = payload["group_by_columns"]
        for col in ("non_striker", "partnership", "batting_position"):
            assert col in group_by_cols, f"{col} should be in group_by_columns"

    def test_partnership_normalize_is_bidirectional(self):
        """
        Partnership values like 'Virat Kohli & AB de Villiers' should collapse
        across both legacy/new name forms and (A,B)/(B,A) ordering when
        merging legacy + new aggregated rows.
        """
        from services.query_builder_v2 import normalize_partnership_for_merge

        aliases = {
            "V Kohli": "Virat Kohli",
            "AB de Villiers": "AB de Villiers",
        }
        a = normalize_partnership_for_merge("V Kohli & AB de Villiers", aliases)
        b = normalize_partnership_for_merge("AB de Villiers & Virat Kohli", aliases)
        assert a == b
        assert a == "AB de Villiers & Virat Kohli"

    def test_batting_position_stage2_join_uses_stage2_source_aliases(self):
        from services.query_builder_v2 import handle_grouped_query

        db = _SqlCaptureDb()
        handle_grouped_query(
            where_clause="WHERE 1=1",
            params={"limit": 10, "offset": 0},
            group_by=["batter", "batting_position"],
            min_balls=1,
            max_balls=None,
            min_runs=None,
            max_runs=None,
            limit=10,
            offset=0,
            db=db,
            filters_applied={},
            has_batter_filters=False,
            show_summary_rows=False,
            join_matches=False,
            min_wickets=None,
            max_wickets=None,
        )

        combined_sql = db.statements[0]
        fallback_sql = db.statements[1]

        assert "stage2_source AS (" in combined_sql
        assert "JOIN stage2_source s ON" in combined_sql
        assert "s.batter IS NOT DISTINCT FROM q.batter" in combined_sql
        assert "s.batting_position IS NOT DISTINCT FROM q.batting_position" in combined_sql
        assert "LEFT JOIN bat_pos bp" in fallback_sql

    def test_partnership_stage2_join_uses_stage2_source_aliases(self):
        from services.query_builder_v2 import handle_grouped_query

        db = _SqlCaptureDb()
        handle_grouped_query(
            where_clause="WHERE 1=1",
            params={"limit": 10, "offset": 0},
            group_by=["partnership"],
            min_balls=None,
            max_balls=None,
            min_runs=500,
            max_runs=None,
            limit=10,
            offset=0,
            db=db,
            filters_applied={},
            has_batter_filters=False,
            show_summary_rows=False,
            join_matches=False,
            min_wickets=None,
            max_wickets=None,
        )

        combined_sql = db.statements[0]
        fallback_sql = db.statements[1]

        assert "stage2_source AS (" in combined_sql
        assert "JOIN stage2_source s ON s.partnership IS NOT DISTINCT FROM q.partnership" in combined_sql
        assert "LEFT JOIN player_aliases pa_bat" in fallback_sql
        assert "LEFT JOIN player_aliases pa_ns" in fallback_sql
