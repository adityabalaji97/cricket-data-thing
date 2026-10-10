"""The special recap's cards on synthetic matches (services/ig_posts/recap_special.py): no database."""
from datetime import date

from services.ig_posts import recap_special as R


def total(mid, inns, bat, bowl, runs, winner, year=2024, country=None, death=None, venue="Ground, Town"):
    t = {"mid": mid, "inns": inns, "bat": bat, "bowl": bowl, "runs": runs, "wkts": 4, "winner": winner,
         "date": f"{year}-01-01", "country": country, "venue": venue, "death_runs": None, "death_balls": None}
    if death:
        t["death_runs"], t["death_balls"] = death
    return t


def ball(inns, over, bat_team, bowl_team, score, wp, kind="spin bowler", length="FULL", control=1, x=1.0, bat="A B"):
    return {"inns": inns, "over": over, "bat": bat, "bowl": "C D", "team_bat": bat_team, "team_bowl": bowl_team,
            "score": score, "bowl_kind": kind, "line": "OFF", "length": length, "control": control, "win_prob": wp,
            "inns_runs": 0, "inns_wkts": 0, "wide": 0, "noball": 0, "x_runs": x, "x_ctl": 0.7}


def match(totals, balls=(), base=None, winner="Chasers", loser="Setters"):
    x = object.__new__(R.Match)
    x.id, x.day, x.sample = "1", date(2026, 10, 9), "sample"
    x.m = {"id": "1", "team1": loser, "team2": winner, "venue": "Ground, Town", "date": x.day}
    x.balls = list(balls)
    x.innings = {i: [b for b in x.balls if b["inns"] == i] for i in (1, 2)}
    x.first_bat, x.first_bowl, x.winner, x.loser = loser, winner, winner, loser
    x.totals = totals
    x.mine = {t["inns"]: t for t in totals if t["mid"] == "1"}
    x.base = base
    return x


def test_chase_record_fires_on_a_record_against_the_loser_and_says_so():
    totals = [total("1", 1, "Setters", "Chasers", 249, "Chasers", 2026), total("1", 2, "Chasers", "Setters", 252, "Chasers", 2026),
              total("2", 2, "Aus", "Setters", 225, "Aus", 2023)] + [total(str(i), 2, "X", "Y", 260 + i, "X") for i in range(10, 22)]
    c = R.chase_record(match(totals))
    assert c and c["facts"]["beat_loser"] and c["facts"]["previous_v_loser"] == 225
    assert "highest ever against Setters" in c["title"]
    assert c["title"].startswith("Chasers' 252")  # possessive of a name ending in s
    assert next(r for r in c["payload"]["rows"] if r["highlight"])["value"] == 252  # shown even outside the top rows


def test_chase_record_quiet_for_an_ordinary_chase():
    totals = [total("1", 1, "Setters", "Chasers", 160, "Chasers"), total("1", 2, "Chasers", "Setters", 161, "Chasers"),
              total("2", 2, "Aus", "Setters", 225, "Aus")] + [total(str(i), 2, "X", "Y", 200 + i, "X") for i in range(10, 22)]
    assert R.chase_record(match(totals)) is None


def test_total_lost_counts_the_losers_big_totals():
    totals = [total("1", 1, "Setters", "Chasers", 249, "Chasers"), total("1", 2, "Chasers", "Setters", 252, "Chasers"),
              total("2", 1, "Setters", "Z", 230, "Z"), total("3", 1, "Setters", "Z", 225, "Setters"),
              total("4", 1, "Setters", "Z", 221, "Setters")]
    c = R.total_lost(match(totals))
    assert c["facts"] == {"rank": 1, "big": 3, "lost_big": 1}
    assert "lost once in 3 innings" in c["help"]


def test_win_probability_is_the_losers_and_the_swing_overs_are_annotated():
    balls = [ball(1, 19, "Setters", "Chasers", 1, 60.0)]  # the setters batting: 60% theirs at the break
    wp = 20.0  # the chasers' chance
    for over in range(4):
        for _ in range(6):
            wp += 10 if over == 2 else 0.5
            balls.append(ball(2, over, "Chasers", "Setters", 6 if over == 2 else 1, wp, bat="Big Hitter"))
    c = R.wp_line(match([], balls))
    assert c["payload"]["start"] == 60.0
    assert c["payload"]["points"][0]["wp"] == 79.5  # 100 - the chasers' 20.5
    (band,) = c["payload"]["bands"]
    assert band["over"] == 3 and band["from"] - band["to"] == 60
    assert band["text"] == "Over 3: D to Hitter, 36 runs"  # no baseline here, so no "usually"
    assert band["bowler"] == "D"


def test_win_probability_quiet_without_a_big_swing_or_a_favourite():
    balls = [ball(1, 19, "Setters", "Chasers", 1, 50.0)] + [ball(2, o, "Chasers", "Setters", 1, 50.0 + o) for o in range(6)]
    assert R.wp_line(match([], balls)) is None


def test_execution_nulls_small_cells_and_compares_with_the_norm():
    base = {("spin bowler", "mid"): {"good": 0.5}, ("pace bowler", "pp"): {"good": 0.4}}
    balls = ([ball(1, 8, "Setters", "Chasers", 1, 50, length="GOOD_LENGTH") for _ in range(4)]
             + [ball(1, 8, "Setters", "Chasers", 1, 50) for _ in range(16)]
             + [ball(1, 2, "Setters", "Chasers", 1, 50, kind="pace bowler") for _ in range(5)]
             + [ball(2, 8, "Chasers", "Setters", 1, 50, length="GOOD_LENGTH") for _ in range(3)]
             + [ball(2, 8, "Chasers", "Setters", 1, 50) for _ in range(12)]
             + [ball(2, 2, "Chasers", "Setters", 1, 50, kind="pace bowler", length="YORKER") for _ in range(13)])
    c = R.execution(match([], balls, base))
    spin, pace = c["payload"]["rows"][1], c["payload"]["rows"][0]
    assert spin["values"] == {"usual": 50, "t0": 20, "t1": 20}  # t0 = Setters bowling (team1), t1 = Chasers
    assert pace["values"]["t1"] is None and pace["pct"]["t1"] is None  # 5 balls: under MIN_CELL
    assert pace["values"]["t0"] == 100
    assert c["kicker"] == "The deeper cut"


def test_conditions_always_says_what_it_cant_measure():
    balls = ([ball(1, 8, "Setters", "Chasers", 1, 50) for _ in range(12)]
             + [ball(2, 8, "Chasers", "Setters", 2, 50) for _ in range(12)])
    x = match([], balls, base={"any": {}})
    c = R.conditions(x)
    assert R.DEW_LINE in c["help"]
    assert c["title"].startswith("Spin went for 2.0 times")  # the chase's spin, against 1.0 in the first innings
    assert next(r for r in c["payload"]["rows"] if r["highlight"])["label"] == "Spin, Chasers batting"


def test_death_pace_says_level_when_the_lead_is_tiny():
    totals = [total("1", 1, "Setters", "Chasers", 249, "Chasers"),
              total("1", 2, "Chasers", "Setters", 252, "Chasers", death=(65, 21)),
              total("2", 2, "Eng", "Z", 230, "Eng", 2023, death=(68, 22))]
    c = R.death_pace(match(totals))
    assert "level with the fastest finish" in c["title"] and "Eng's 68 off 22" in c["title"]


def test_possessives():
    assert R.poss("West Indies") == "West Indies'" and R.poss("India") == "India's"
