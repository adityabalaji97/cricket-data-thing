from services import jev_client, match_recap


class _NoRows:
    """DB stand-in: no par and no ball-level rows, so only scorecard facts appear."""

    def execute(self, *_a, **_k):
        return self

    def mappings(self):
        return self

    def first(self):
        return None


def _scorecard():
    return {
        "match": {"id": "t1", "team1": "Mumbai Indians", "team2": "Chennai Super Kings", "winner": "Chennai Super Kings",
                  "result_text": "Chennai Super Kings won by 8 wickets", "chase_note": "Chased 160 with 11 balls to spare",
                  "competition": "IPL", "date": "2026-05-02"},
        "summary": {
            "innings_scores": [{"batting_team": "Mumbai Indians", "runs": 159, "wickets": 7}],
            "primer": {"win_probability": {"team": "Mumbai Indians", "points": [0.5, 0.8, 0.6, 0.1]}},
        },
        "innings": [
            {"batting": [{"name": "Naman Dhir", "team": "Mumbai Indians", "runs": 57, "balls": 37, "not_out": False, "impact": 12.0, "wpa": 0.09},
                         {"name": "Will Jacks", "team": "Mumbai Indians", "runs": 1, "balls": 5, "impact": -16.7, "wpa": -0.13}],
             "bowling": [{"name": "Noor Ahmad", "team": "Chennai Super Kings", "wickets": 2, "runs": 27, "overs": "4.0", "impact": 18.2, "wpa": 0.1}]},
        ],
    }


def test_recap_facts_are_written_from_the_scorecard():
    texts = [f["text"] for f in match_recap.build_recap_facts(_scorecard(), _NoRows())]
    assert "Naman Dhir's 57 off 37 added 12.0 runs to Mumbai Indians' expected total (Impact; win probability +9%)." in texts
    assert "Will Jacks' 1 off 5 cost Mumbai Indians 16.7 runs against expected (Impact)." in texts
    assert "Noor Ahmad's 2/27 in 4 overs saved 18.2 runs (Impact) for Chennai Super Kings." in texts
    assert "Chennai Super Kings won from as low as 20% win probability." in texts


def test_recap_without_jev_orders_by_effect_size(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    match_recap._CACHE.clear()
    recap = match_recap.build_recap(_scorecard(), _NoRows())
    assert recap["source"] == "deterministic"
    assert recap["headline"] == "Chennai Super Kings won from as low as 20% win probability."
    assert recap["bullets"][-1].startswith("Chennai Super Kings won by 8 wickets")


def test_recap_uses_jev_ranking_when_there_is_no_big_picture_fact(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test")
    match_recap._CACHE.clear()
    monkeypatch.setattr(jev_client, "ask", lambda state, questions, timeout=3.0: {
        qid: {"score": 3.9 if "Noor Ahmad" in q["instructions"] else 1.0} for qid, q in questions.items()})
    scorecard = _scorecard()
    scorecard["summary"]["primer"]["win_probability"]["points"] = [0.5, 0.45, 0.4, 0.35]  # no comeback
    recap = match_recap.build_recap(scorecard, _NoRows())
    assert recap["source"] == "typed"
    assert recap["headline"].startswith("Noor Ahmad")


def test_big_picture_facts_lead_whatever_jev_prefers(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test")
    match_recap._CACHE.clear()
    # Jev prefers a bowling spell, but the comeback (big picture) must still lead.
    monkeypatch.setattr(jev_client, "ask", lambda state, questions, timeout=3.0: {
        qid: {"score": 3.9 if "Noor Ahmad" in q["instructions"] else 1.0} for qid, q in questions.items()})
    recap = match_recap.build_recap(_scorecard(), _NoRows())
    assert recap["headline"] == "Chennai Super Kings won from as low as 20% win probability."
    assert recap["bullets"][0].startswith("Noor Ahmad")
