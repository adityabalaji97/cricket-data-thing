"""The bowling grid's rows (MOTION_REEL_PLAN.md, owner's decision 5): the five who bowl the most overs per match,
all shown, best first (carousel and Reel alike since 18 Nov 2026)."""
from services.squad_view import regular_attack


def b(name, balls, games, raa, played=None):
    """A bowler: `games` bowling innings, `played` matches (his batting innings stand in; defaults to games)."""
    return {"name": name, "bowl_balls": balls, "bowl_raa": raa, "bowl": {"innings_count": games},
            "bat": {"innings_count": played if played is not None else games}}


def test_five_who_bowl_most_per_match_best_first():
    players = [
        b("workhorse", 480, 20, -30),      # 24 a match, below par: still shown
        b("strike", 300, 13, 40),          # 23 a match
        b("death", 330, 15, 10),           # 22 a match
        b("spinner", 400, 20, 5),          # 20 a match
        b("fifth", 270, 15, -5),           # 18 a match
        b("light_load", 250, 20, 60),      # 12.5 a match: bowls every game, but only two overs or so
        b("barely", 40, 2, 99),            # under the minimum balls
    ]
    rows = regular_attack(players)
    assert [p["name"] for p in rows] == ["strike", "death", "spinner", "fifth", "workhorse"]  # five, best first
    assert "workhorse" in [p["name"] for p in rows]  # a below-par regular is never left out


def test_a_part_timer_with_three_full_spells_is_not_a_regular():
    # The side played 14 matches. The part-timer bowled his four overs in 3 of them (24 a bowling innings, 72 balls);
    # the regular bowled 20 a match in all 14. Per bowling innings the part-timer would rank first.
    players = [b("regular", 280, 14, -10)] + [b(f"r{i}", 260 - 10 * i, 14, i) for i in range(4)]
    players.append(b("part_timer", 72, 3, 5, played=14))
    names = [p["name"] for p in regular_attack(players)]
    assert "part_timer" not in names
    assert "regular" in names


def test_a_part_timer_over_matches_he_played_not_innings_he_bowled():
    # Bowled in 6 of his 12 matches (a third of the side's 14 clears the floor), 24 balls each time: 12 a match, so
    # he ranks below a regular on 18 a match, though per bowling innings (24) he'd be top.
    players = [b("reg", 252, 14, 1)] + [b("occasional", 144, 6, 9, played=12)]
    assert [p["name"] for p in regular_attack(players, n=1)] == ["reg"]


def test_fewer_than_five_bowlers_shows_them_all():
    rows = regular_attack([b("a", 200, 10, 1), b("b", 100, 10, -1)])
    assert [p["name"] for p in rows] == ["a", "b"]


def test_no_innings_count_does_not_crash():
    rows = regular_attack([{"name": "x", "bowl_balls": 120, "bowl_raa": 3, "bowl": None, "games": 5}, b("y", 120, 5, 1)])
    assert {p["name"] for p in rows} == {"y"}  # x has no bowling innings on record: below the floor
