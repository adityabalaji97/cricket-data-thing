from services import storyline_testers as T


def test_verdict_follows_the_claims_direction_and_the_gap():
    assert T._verdict("up", 15, True) == "supported"
    assert T._verdict("up", -15, True) == "not supported"
    assert T._verdict("down", -15, True) == "supported"
    assert T._verdict("up", 3, True) == "partly"          # about his usual
    assert T._verdict("neither", 30, True) == "context"   # a claim with no direction gets the numbers, no verdict
    assert T._verdict("up", 30, False) == "too little data"


def test_untestable_kinds_are_context(monkeypatch):
    out = T.run(None, {"id": 1, "kind": "injury", "claim": "x", "players": [], "team": None}, {"format": "T20I"})
    assert out["verdict"] == "context" and out["finding"] is None
