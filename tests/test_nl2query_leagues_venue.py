"""12 Nov 2026 fixes: every league the data holds survives validation (SMAT questions lost their filter); a side's name
isn't read as its home ground ("Mumbai Indians in 2026" got the Wankhede); conditions no filter can express reach the
reader as warnings."""
from services import nl2query


def _parsed(filters, **extra):
    return {"filters": filters, "group_by": ["bowler"], "confidence": "high", **extra}


def test_smat_and_other_domestic_leagues_survive_validation():
    out = nl2query.validate_filters(_parsed({"leagues": ["SMAT", "Super Smash", "MLC", "Not A League"]}), "SMAT bowlers")
    assert out["filters"]["leagues"] == ["SMAT", "Super Smash", "MLC"]


def test_team_name_is_not_its_home_ground():
    out = nl2query.validate_filters(_parsed({"batting_teams": ["Mumbai Indians"], "venue": "Mumbai"}), "Mumbai Indians in 2026")
    assert "venue" not in out["filters"]
    post = nl2query._post_process_result("Mumbai Indians in 2026", {"filters": {"batting_teams": ["Mumbai Indians"]}, "group_by": []})
    assert "venue" not in post["filters"]


def test_a_named_ground_is_kept():
    out = nl2query.validate_filters(_parsed({"batters": ["Virat Kohli"], "venue": "M Chinnaswamy Stadium"}), "Virat Kohli at Chinnaswamy")
    assert out["filters"]["venue"] == "M Chinnaswamy Stadium"


def test_unapplied_conditions_become_warnings():
    out = nl2query.validate_filters(_parsed({"over_min": 15}, not_applied=["on Indian pitches", "who have not played IPL in 2026"]),
                                    "death bowlers on Indian pitches who have not played IPL in 2026")
    assert out["warnings"] == ["Couldn't apply: on Indian pitches", "Couldn't apply: who have not played IPL in 2026"]
