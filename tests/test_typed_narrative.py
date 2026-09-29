from services import jev_client, typed_preview


def _context():
    return {
        "team1": "Mumbai Indians",
        "team2": "Chennai Super Kings",
        "venue": "Wankhede Stadium, Mumbai",
        "elo": {"Mumbai Indians": 1468, "Chennai Super Kings": 1530},
        "match_history": {
            "team1_recent": {"sample_size": 5, "wins_batting_first": 0, "wins_chasing": 2,
                             "chasing_scores": [{"won": False}, {"won": True}, {"won": True}]},
            "team2_recent": {"sample_size": 5, "wins_batting_first": 3, "wins_chasing": 1},
        },
        "screen_story": {
            "match_results_distribution": {"venue_toss_signal": {"batting_first_wins": 51, "chasing_wins": 70, "total_matches": 122}},
            "innings_scores_analysis": {"avg_winning_score_rounded": 197, "avg_chasing_score_rounded": 166,
                                        "highest_total_chased": 243, "lowest_total_defended": 118},
            "head_to_head_stats": {"overall_window_summary": {"sample_size": 10, "team1_wins": 2, "team2_wins": 8}},
            "expected_fantasy_points": {
                "batting_edges": {"Mumbai Indians": [{"batter": "Suryakumar Yadav", "bowler": "Zak Foulkes", "balls": 14, "runs": 43, "strike_rate": 307.1}]},
                "bowling_threats": {"Mumbai Indians": [{"bowler": "Jasprit Bumrah", "balls": 298, "wickets": 16, "economy": 6.44}]},
            },
        },
    }


def test_facts_are_single_claims_written_from_the_numbers():
    texts = [f["text"] for f in typed_preview.build_candidate_facts(_context())]
    assert "Chasing sides have won 70 of 122 matches at Wankhede Stadium, Mumbai." in texts
    assert "Chennai Super Kings lead Mumbai Indians 8-2 in their last 10 meetings." in texts
    assert "Mumbai Indians won 2 of their last 3 chases." in texts
    assert "Suryakumar Yadav has scored 43 off 14 balls against Zak Foulkes (strike rate 307)." in texts
    assert "Jasprit Bumrah has 16 wickets in 298 balls against Chennai Super Kings' likely batters, at 6.44 an over." in texts
    assert "Chennai Super Kings are rated 62 Elo points higher." in texts


def test_no_key_means_no_call_and_no_typed_preview(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setattr(jev_client.httpx, "post", lambda *a, **k: (_ for _ in ()).throw(AssertionError("called")))
    assert typed_preview.curate(_context()) is None


def test_curation_keeps_the_best_per_section_and_picks_a_headline(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test")
    facts = typed_preview.build_candidate_facts(_context())
    h2h_id = next(f["id"] for f in facts if f["kind"] == "h2h")

    def fake_ask(state, questions, timeout=3.0):
        assert set(questions) == {f["id"] for f in facts if not f["fixed"]}
        return {qid: {"type": "score", "score": 3.8 if qid == h2h_id else 1.0 + int(qid[1:]) % 3 * 0.6} for qid in questions}

    monkeypatch.setattr(jev_client, "ask", fake_ask)
    result = typed_preview.curate(_context(), facts)
    assert result["headline"] == "Chennai Super Kings lead Mumbai Indians 8-2 in their last 10 meetings."
    by_id = {s["id"]: s for s in result["sections"]}
    for section in by_id.values():
        curated = [b for b in section["bullets"] if not b.startswith(("Too close", "Lean"))]
        assert 1 <= len(curated) <= typed_preview.MAX_PER_SECTION or section["id"] == "preview_take"
    assert by_id["preview_take"]["bullets"][0].startswith("Too close to call")


def test_failed_jev_call_falls_back(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test")
    monkeypatch.setattr(jev_client, "ask", lambda *a, **k: None)
    assert typed_preview.curate(_context()) is None
