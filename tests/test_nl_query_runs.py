"""Relative dates resolve from today, and what happens after a question is parsed is recorded."""
from datetime import date
from unittest.mock import MagicMock

import pytest

from services import nl2query

TODAY = date(2026, 10, 15)


@pytest.fixture
def today(monkeypatch):
    monkeypatch.setattr(nl2query, "_today", lambda: TODAY)
    return TODAY


@pytest.fixture
def runs(monkeypatch):
    """Rows record_nl_run hands to the usage-log queue."""
    captured = []
    monkeypatch.setattr("services.usage_log.enqueue", lambda kind, row: captured.append((kind, row)))
    return captured


@pytest.mark.parametrize("question,start,end", [
    ("What lengths are most wicket taking in pp venue wise in last 3 years", "2023-10-15", None),
    ("IPL venue wise data by bowl kind in pp last three years", "2023-10-15", None),
    ("Shreyas iyer vs line and length in last 1 year", "2025-10-15", None),
    ("kohli in the past 18 months", "2025-04-15", None),
    ("how has kusal mendis's batting changed over the last two years", "2024-10-15", None),
    ("bumrah in the last year", "2025-10-15", None),
    ("bumrah over the past year", "2025-10-15", None),
    ("best death bowlers last year", "2025-01-01", "2025-12-31"),
    ("rashid khan since last year", "2025-01-01", None),
    ("most sixes this year", "2026-01-01", None),
])
def test_relative_windows_count_back_from_today(question, start, end):
    assert nl2query._relative_date_window(question.lower(), TODAY) == {"start_date": start, "end_date": end}


def test_no_relative_window_for_plain_or_absolute_dates():
    assert nl2query._relative_date_window("kohli vs spin since 2023", TODAY) is None
    assert nl2query._relative_date_window("csk powerplay batting over the years", TODAY) is None
    assert nl2query._years_before(date(2028, 2, 29), 1) == date(2027, 2, 28)


def test_model_dates_from_its_own_sense_of_now_are_replaced(today):
    """On 15 Oct 2026 the model turned "last 3 years" into 2021-2023."""
    result = nl2query._post_process_result(
        "What lengths are most wicket taking in pp venue wise in last 3 years",
        {"filters": {"start_date": "2021-01-01", "end_date": "2023-12-31", "over_max": 5},
         "group_by": ["venue", "length"]},
    )
    assert result["filters"]["start_date"] == "2023-10-15"
    assert "end_date" not in result["filters"]
    assert "2023-10-15" in result["explanation"]


def test_explicit_range_is_left_alone(today):
    result = nl2query._post_process_result(
        "kohli between 2019 and 2021, not the last 3 years",
        {"filters": {"start_date": "2019-01-01", "end_date": "2021-12-31"}, "group_by": ["batter"]},
    )
    assert result["filters"]["start_date"] == "2019-01-01"
    assert result["filters"]["end_date"] == "2021-12-31"


def test_prompt_carries_todays_date_and_cache_is_per_day(today, monkeypatch):
    sent = {}

    class FakeCompletions:
        def create(self, **kw):
            sent.update(kw)
            msg = MagicMock()
            msg.message.content = '{"filters": {}, "group_by": ["batter"]}'
            return MagicMock(choices=[msg], usage=None)

    fake = MagicMock()
    fake.chat.completions = FakeCompletions()
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setattr(nl2query, "OpenAI", lambda api_key: fake)
    nl2query.call_openai("kohli last 3 years")
    system = sent["messages"][0]["content"]
    assert "Today's date is 2026-10-15" in system
    assert "2023-10-15" in system

    key_today = nl2query._get_cache_key("Kohli last 3 years")
    monkeypatch.setattr(nl2query, "_today", lambda: date(2026, 10, 16))
    assert nl2query._get_cache_key("Kohli last 3 years") != key_today


def test_parse_row_with_a_run_to_follow_waits_for_it():
    db = MagicMock()
    db.execute.return_value.fetchone.return_value = (7,)
    nl2query.persist_nl_query_log("kohli", {"success": True, "filters": {}, "group_by": ["batter"]}, None, 10,
                                  db=db, log_ref="abc")
    params = db.execute.call_args[0][1]
    assert params["log_ref"] == "abc"
    assert params["execution_success"] is None  # not run yet

    nl2query.persist_nl_query_log("kohli", {"success": False}, None, 10, db=db, log_ref="abc")
    assert db.execute.call_args[0][1]["execution_success"] is False

    nl2query.persist_nl_query_log("kohli", {"success": True}, None, 10, db=db)  # summaries: no run follows
    assert db.execute.call_args[0][1]["execution_success"] is True


def test_record_nl_run(runs):
    nl2query.record_nl_run("abc", "empty", rows=0, ms=40)
    nl2query.record_nl_run(None, "ok")
    nl2query.record_nl_run("abc", "weird")
    assert runs == [("nl_run", {"log_ref": "abc", "status": "empty", "ok": True, "rows": 0, "ms": 40, "error": None})]


def test_parse_endpoint_returns_a_log_ref(client, monkeypatch):
    from routers import nl2query as router

    logged = {}
    monkeypatch.setattr(router, "parse_nl_query", lambda query, db=None: {
        "success": True, "filters": {}, "group_by": ["batter"], "confidence": "high"})
    monkeypatch.setattr(router, "log_nl_query_event_background", lambda **kw: logged.update(kw))
    payload = client.post("/nl2query/parse", json={"query": "kohli by year"}).json()
    assert payload["log_ref"] and payload["log_ref"] == logged["log_ref"]


def test_deliveries_run_records_its_outcome(client, monkeypatch, runs):
    from routers import query_builder_v2

    monkeypatch.setattr(query_builder_v2, "run_deliveries_query",
                        lambda db, **kw: {"data": [{"batter": "V Kohli"}, {"batter": "RG Sharma"}], "metadata": {}})
    assert client.get("/query/deliveries?group_by=batter&nl_ref=abc").status_code == 200
    assert client.get("/query/deliveries?group_by=batter").status_code == 200  # not from a question: nothing
    assert [(k, r["status"], r["rows"]) for k, r in runs] == [("nl_run", "ok", 2)]

    def boom(db, **kw):
        raise query_builder_v2.QueryValidationError("over_max must be <= 19")

    monkeypatch.setattr(query_builder_v2, "run_deliveries_query", boom)
    assert client.get("/query/deliveries?group_by=batter&nl_ref=abc").status_code == 422
    assert runs[-1][1]["status"] == "error" and "over_max" in runs[-1][1]["error"]


def test_refused_graphic_idea_records_why(monkeypatch, runs):
    from services import content_ideas
    from services.snapshots import SnapshotError

    logged = []
    monkeypatch.setattr("services.nl2query.parse_nl_query",
                        lambda idea, db=None: {"success": True, "filters": {}, "group_by": []})
    monkeypatch.setattr("services.nl2query.log_nl_query_event_background", lambda **kw: logged.append(kw))
    with pytest.raises(SnapshotError):
        content_ideas.plan("kusal mendis", None, None, client="1.2.3.4")
    assert logged[0]["log_ref"] == runs[0][1]["log_ref"]
    assert runs[0][1]["status"] == "refused" and "no grouping" in runs[0][1]["error"]


def test_graphic_attempt_outcome_is_recorded(client, monkeypatch, runs):
    from routers import snapshots

    monkeypatch.setattr(snapshots, "_allow_idea", lambda client, db=None: True)
    monkeypatch.setattr("services.content_ideas.plan", lambda idea, fmt, db, client: {"log_ref": "g1", "params": {}})
    monkeypatch.setattr("services.content_ideas.attempt",
                        lambda db, idea, planned, created_by: {"status": "parked", "note": "No rows for this."})
    assert client.post("/snapshots/idea", json={"text": "best batters against spin"}).status_code == 400
    assert runs[-1][1] == {"log_ref": "g1", "status": "no_chart", "ok": False, "rows": None,
                           "ms": runs[-1][1]["ms"], "error": "No rows for this."}
