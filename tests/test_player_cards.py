from services.player_cards import start_curve
from services.player_verdict import verdict_rows


def _rows(innings):
    out = []
    for i, balls in enumerate(innings):
        for n, (runs, impact) in enumerate(balls, 1):
            out.append({"match_id": str(i), "innings": 1, "batter_ball_number": n, "runs": runs, "balls": 1, "impact": impact})
    return out


def test_start_curve_carries_finished_innings_and_counts_alive():
    c = start_curve(_rows([[(4, 3), (0, -1), (6, 5)], [(0, -10)]]))
    assert c["innings"] == 2
    b1, b3 = c["points"][0], c["points"][2]
    assert b1["alive"] == 2 and b1["sr_ball"] == 200.0 and b1["sr_cum"] == 200.0
    assert b3["alive"] == 1 and b3["sr_ball"] == 600.0
    assert b3["sr_cum"] == round(100 * 10 / 4, 1)  # 10 runs off the 4 balls faced by then
    assert b3["par"] == round((7 + -10) / 2, 1)  # median of the running totals, the dismissed innings carried


def test_verdict_rows_rank_then_standouts():
    s = {"primary_role": "bat", "allrounder": False, "has_wins_added": False, "roles": {"bat": {
        "peers": {"qualified": True, "metrics": [{"key": "strike_rate", "label": "Strike rate", "rank": 3, "n": 300}]},
        "standouts": [{"words": "boundary %", "where": "against spin", "value": 33.0, "format": "pct", "rank": 2,
                       "n": 321, "share": 2 / 321},
                      {"words": "false shots forced", "where": "at the death", "value": 45.5, "format": "pct", "rank": 30,
                       "n": 400, "share": 0.075}],
        "seasons": []}}}
    assert verdict_rows(s) == [
        {"rank": "3rd of 300", "what": "Strike rate", "lead": True},
        {"rank": "2nd of 321", "what": "Boundary %, v spin · 33%", "lead": False},
        {"rank": "Top 10%", "what": "False shots, death · 46%", "lead": False},
    ]
