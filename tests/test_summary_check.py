from services import jev_client, summary_check

PATTERNS = {"overall_strike_rate": 199.6, "overall_boundary_percentage": 33.27, "phase_distribution": {"powerplay": 64.7},
            "strengths": [{"context": "vs spin", "strike_rate": 262.79, "average": 37.67, "balls": 43}], "typical_batting_position": 1}


def test_numbers_must_match_the_data_to_the_precision_shown():
    known = list(summary_check._walk_numbers(PATTERNS))
    assert summary_check.numbers_supported("SR 200, 33.3% boundaries", known)[0]
    assert summary_check.numbers_supported("bats at #1 in overs 16-20", known)[0]
    ok, bad = summary_check.numbers_supported("strength score of 3.46 in 100% of innings", known)
    assert not ok and bad == ["3.46", "100"]


def test_failing_lines_fall_back_to_the_deterministic_line_for_that_topic(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    text, report = summary_check.verify_lines(
        "⚡ Style: SR 200 with 33.3% boundaries\n💪 Sweet Spot: vs spin, strength score 3.46",
        PATTERNS, fallback_text="💪 Sweet Spot: Strong vs spin (SR 263, Avg 37.7)")
    assert text.split("\n") == ["⚡ Style: SR 200 with 33.3% boundaries", "💪 Sweet Spot: Strong vs spin (SR 263, Avg 37.7)"]
    assert len(report["replaced"]) == 1


def test_jev_drops_misattributed_claims(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test")
    monkeypatch.setattr(jev_client, "ask", lambda state, questions, timeout=3.0: {
        qid: {"noul": 0.2 if "runs" in q["instructions"] else 0.9} for qid, q in questions.items()})
    text, report = summary_check.verify_lines(
        "🎯 Role: 64.7% of balls in the powerplay\n⚡ Style: 33.3% of his runs in boundaries", PATTERNS)
    assert text == "🎯 Role: 64.7% of balls in the powerplay"
    assert report["dropped"][0]["support"] == 0.2
