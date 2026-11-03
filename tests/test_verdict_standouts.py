from services.player_verdict import _signed, _standout_text, standouts, verdict_line


def _pool(n=40):
    rows = {f"P{i}": {"balls": 200, "strike_rate": 100 + i, "boundary_percentage": 10 + i / 10} for i in range(n)}
    rows["Me"] = {"balls": 200, "strike_rate": 500, "boundary_percentage": 11}
    small = {f"P{i}": {"balls": 200, "strike_rate": 100 + i, "boundary_percentage": 10} for i in range(n)}
    small["Me"] = {"balls": 50, "strike_rate": 900, "boundary_percentage": 90}  # under the split's minimum
    return {"splits": {"phase:powerplay": rows, "phase:death": small}}


def test_best_split_only_when_top_ten_percent_and_enough_balls():
    out = standouts(_pool(), "bat", "Me")
    assert [(f["split"], f["key"], f["rank"]) for f in out] == [("phase:powerplay", "strike_rate", 1)]


def test_no_standouts_without_pool_or_player():
    assert standouts(None, "bat", "Me") == []
    assert standouts(_pool(), "bat", "Nobody") == []


def test_small_pools_are_ignored():
    assert standouts(_pool(n=10), "bat", "Me") == []


def test_text_and_zero_sign():
    f = {"words": "strike rate", "where": "in the powerplay", "value": 197.4, "format": "int", "rank": 2, "n": 280, "share": 2 / 280}
    assert _standout_text(f) == "strike rate in the powerplay (197, 2nd of 280)"
    assert _signed(-0.01) == "0.0" and _signed(1.2) == "+1.2"


def test_verdict_line_appends_standouts_and_headline_omits_them():
    s = {"primary_role": "bat", "allrounder": False, "has_wins_added": False, "roles": {"bat": {
        "peers": {"qualified": True, "metrics": [{"key": "strike_rate", "label": "Strike rate", "rank": 3, "n": 300}]},
        "standouts": [{"words": "boundary %", "where": "against spin", "value": 33, "format": "pct", "rank": 2,
                       "n": 321, "share": 2 / 321}],
        "seasons": []}}}
    assert verdict_line(s) == "3rd of 300 for strike rate. Stands out for boundary % against spin (33%, 2nd of 321)."
    assert verdict_line(s, with_standouts=False) == "3rd of 300 for strike rate."
