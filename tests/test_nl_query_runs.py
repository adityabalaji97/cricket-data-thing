"""Relative dates resolve from today, and what happens after a question is parsed is recorded."""
import json
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
    monkeypatch.setattr(nl2query, "OpenAI", lambda api_key, **kw: fake)
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
    monkeypatch.setattr(router, "parse_nl_query", lambda query, db=None, fmt=None: {
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
                        lambda idea, db=None, fmt=None: {"success": True, "filters": {}, "group_by": []})
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


def test_reasoning_models_get_the_arguments_they_accept():
    assert nl2query.chat_kwargs("gpt-4o", 500, temperature=0.2) == {"temperature": 0.2, "max_tokens": 500}
    luna = nl2query.chat_kwargs("gpt-6-luna", 1000, reasoning_effort="low", service_tier="fast")
    assert luna["reasoning_effort"] == "low" and luna["service_tier"] == "fast"
    assert luna["max_completion_tokens"] > 1000 and "temperature" not in luna and "max_tokens" not in luna


def test_fast_mode_bills_double_and_stops_at_the_cap(monkeypatch):
    assert nl2query.estimate_cost("gpt-6-luna", 1_000_000, 0, "fast") == pytest.approx(0.20)
    assert nl2query.estimate_cost("gpt-6-luna", 1_000_000, 0) == pytest.approx(0.10)
    monkeypatch.setattr(nl2query, "_month_spend", lambda db: 3.0)
    assert nl2query.select_service_tier(object()) == "fast"
    monkeypatch.setattr(nl2query, "_month_spend", lambda db: nl2query.MONTHLY_COST_CAP + 1)
    assert nl2query.select_service_tier(object()) is None
    monkeypatch.setattr(nl2query, "FAST_MODE", False)
    monkeypatch.setattr(nl2query, "_month_spend", lambda db: 0.0)
    assert nl2query.select_service_tier(object()) is None


def test_a_failed_primary_call_falls_back(monkeypatch):
    from openai import APITimeoutError

    nl2query._cache.clear()
    calls = []

    def fake(query, few_shot_examples=None, model=None, reasoning_effort=None, service_tier=None, page_format=None, **_kw):
        calls.append((model, service_tier))
        if model == nl2query.MODEL_PRIMARY:
            raise APITimeoutError(request=MagicMock())
        return {"filters": {}, "group_by": ["batter"], "confidence": "high"}

    monkeypatch.setattr(nl2query, "call_openai", fake)
    monkeypatch.setattr(nl2query, "select_service_tier", lambda db=None: "fast")
    result = nl2query.parse_nl_query("best death bowlers fallback test")
    assert result["success"] is True
    assert calls == [(nl2query.MODEL_PRIMARY, "fast"), (nl2query.MODEL_FALLBACK, None)]


def test_few_shot_examples_show_only_the_fields_the_model_returns():
    out = json.loads(nl2query._serialize_few_shot_output({
        "parsed_filters": {"batters": ["Virat Kohli"]}, "group_by": ["batter"], "explanation": "old",
        "interpretation": {"summary": "old"}}))
    assert "explanation" not in out and "interpretation" not in out
    assert out["filters"] == {"batters": ["Virat Kohli"]}


@pytest.mark.parametrize("question,kept", [
    ("kusal mendis wagon zones", False),
    ("Bumrah economy by season since 2018", False),
    ("Kohli vs pace compared to other IPL batters, 150+ balls", True),
    ("Rashid Khan economy, minimum 300 balls", True),
    ("Shubman Gill strike rate among IPL openers", True),
])
def test_no_automatic_ball_floor_on_a_named_players_breakdown(question, kept):
    result = nl2query._post_process_result(question, {"filters": {"min_balls": 20, "batters": ["X"]},
                                                      "group_by": ["year"]})
    assert ("min_balls" in result["filters"]) is kept


def test_odi_questions_never_get_the_t20i_league():
    result = nl2query._post_process_result("Shai Hope ODI batting compared to others",
                                           {"filters": {"leagues": ["T20I"]}, "group_by": ["batter"]})
    assert "leagues" not in result["filters"]
    result = nl2query._post_process_result("Rohit in T20Is and ODIs",
                                           {"filters": {"leagues": ["T20I"]}, "group_by": ["batter"]})
    assert result["filters"]["leagues"] == ["T20I"]


@pytest.mark.parametrize("question,page,fmt,overs", [
    ("Rohit sharma ODI powerplay batting average and strike rate by year", None, "ODI", (0, 9)),
    ("death overs economy for IPL bowlers", "ODI", "T20", (15, 19)),       # the question's format wins
    ("death overs economy since 2023", "ODI", None, (40, 49)),             # else the page's
    ("death overs economy since 2023", None, None, (15, 19)),              # else T20's
    ("middle overs strike rate in one-day internationals", None, "ODI", (10, 39)),
    ("kohli in overs 40-49 in ODIs", None, "ODI", (40, 49)),               # the user's own overs stay
    ("Kohli powerplay vs death strike rate", "ODI", None, (None, None)),   # two phases: no single window
    ("middle order batters in ODIs", None, "ODI", (None, None)),           # not "middle overs"
    ("Joe Root test career by year", None, "TEST", (None, None)),
])
def test_phases_follow_the_format(question, page, fmt, overs):
    filters = {"over_min": 40, "over_max": 49} if "40-49" in question else {}
    result = nl2query._post_process_result(question, {"filters": filters, "group_by": ["batter"]}, page_format=page)
    assert result["format"] == fmt
    assert (result["filters"].get("over_min"), result["filters"].get("over_max")) == overs


def test_overs_are_held_to_the_formats_cap_and_format_grouping_survives():
    validated = nl2query.validate_filters({"filters": {"over_min": 40, "over_max": 49}, "group_by": ["format"]}, "")
    assert validated["filters"]["over_max"] == 49 and validated["group_by"] == ["format"]
    t20 = nl2query._post_process_result("IPL batters", {"filters": {"over_min": 40, "over_max": 49},
                                                         "group_by": ["batter", "format"]})
    assert t20["filters"]["over_max"] == 19 and "format" not in t20["group_by"]
    both = nl2query._post_process_result("kohli in T20 and ODI by format", {"filters": {}, "group_by": ["batter", "format"]})
    assert both["format"] is None and "format" in both["group_by"]


def test_the_page_format_reaches_the_prompt_and_the_cache(monkeypatch):
    nl2query._cache.clear()
    seen = []

    def fake(query, page_format=None, **kw):
        seen.append(page_format)
        return {"filters": {}, "group_by": ["batter"], "confidence": "high"}

    monkeypatch.setattr(nl2query, "call_openai", fake)
    monkeypatch.setattr(nl2query, "select_service_tier", lambda db=None: None)
    nl2query.parse_nl_query("best death bowlers", fmt="ODI")
    nl2query.parse_nl_query("best death bowlers", fmt="T20")
    nl2query.parse_nl_query("best death bowlers", fmt="ODI")  # cached
    assert seen == ["ODI", "T20"]
    assert "set to ODI" in nl2query._format_context("ODI") and "all formats" in nl2query._format_context("ALL")


def test_every_text_caller_is_off_gpt_4o():
    from routers import match_preview, player_summary
    from services import ig_reel_v2, llm

    assert {player_summary.OPENAI_MODEL, match_preview.OPENAI_MODEL, nl2query.MODEL_PRIMARY} == {llm.MODEL_LIGHT}
    assert {ig_reel_v2.SCRIPT_MODEL, nl2query.MODEL_FALLBACK} == {llm.MODEL_STRONG}
    assert match_preview._is_gpt5_model()  # reasoning models take the Responses path
