"""The record holder's profile (services/ig_posts/record_profile.py) and the T20I scope fix: no database."""
from datetime import date

from services import idea_stats as S
from services.ig_posts import record_profile as RP


def test_t20i_scope_keeps_a_sides_out():
    where, params = S._where({"fmt": "T20", "league": "T20I"}, "s.batting_team", S._opp("s.batting_team"))
    assert "m.competition = ANY(:intl)" in where and params["intl"] == ["T20I"]


def test_opponent_list_scope():
    where, params = S._where({"fmt": "T20", "league": "T20I", "opponents": ["India", "Australia"]}, "dd.team_bat", "dd.team_bowl")
    assert "dd.team_bowl = ANY(:opps)" in where and params["opps"] == ["India", "Australia"]


def test_associates_are_flagged():
    assert RP.associate("Austria") and not RP.associate("India") and not RP.associate(None)
    assert RP.label({"name": "Karanbir Singh", "team": "Austria"}).endswith("†")
    assert RP.label({"name": "Suryakumar Yadav", "team": "India"}) == "Suryakumar"


POOL = [{"name": "A One", "date": date(2026, 10, 11), "team": "India"},
        {"name": "B Two", "date": date(2023, 1, 1), "team": "India"}]


def fake_qb(totals, phases):
    def qb(db, name, until, group_by, **extra):
        if group_by == ["batter"]:
            return [totals[name]]
        return []
    return qb


def phase_rows(wpa):
    return {k: {"phase": k, "balls": 300, "wpa": w * 3, "metric_balls": 300, "avg_leverage": 0.1}
            for k, w in zip(("powerplay", "middle"), wpa)}


def test_deep_cut_needs_different_raa_and_wpa_leaders(monkeypatch):
    by_phase = {"A One": phase_rows((0.34, 0.09)), "B Two": phase_rows((0.25, 0.35))}
    split = {"A One": {"raa_per_100": 64, "wpa": 2.7, "metric_balls": 1000},
             "B Two": {"raa_per_100": 36, "wpa": 3.8, "metric_balls": 1000}}
    monkeypatch.setattr(RP, "_qb", fake_qb(split, by_phase))
    monkeypatch.setattr(RP, "past_powerplay", lambda db, name, until: {"innings": 25, "runs": 930, "balls": 394,
                                                                         "sr": 236, "wp0": 63, "wp6": 64})
    c = RP.deep_card(None, POOL, by_phase, "")
    assert c and c["kicker"] == "The deeper cut" and "most of all in the middle overs" in c["title"]
    # His own start already tilted the game: the card says so, rather than that his later runs matter less.
    monkeypatch.setattr(RP, "past_powerplay", lambda db, name, until: {"innings": 25, "runs": 930, "balls": 394,
                                                                         "sr": 236, "wp0": 63, "wp6": 76})
    c = RP.deep_card(None, POOL, by_phase, "")
    assert c["title"] == "One adds the most runs above average, and he does it up front"
    assert "from 63% to 76%" in c["help"] and "low stakes" not in c["help"]
    assert [r["label"] for r in c["payload"]["rows"] if r.get("highlight")] == ["Powerplay"]
    same = {"A One": {"raa_per_100": 64, "wpa": 4.0, "metric_balls": 1000}, "B Two": split["B Two"]}
    monkeypatch.setattr(RP, "_qb", fake_qb(same, by_phase))
    assert RP.deep_card(None, POOL, by_phase, "") is None


def test_opposition_drops_players_without_enough_balls():
    pool = POOL + [{"name": "C Three", "date": date(2024, 1, 1), "team": "Austria"},
                   {"name": "D Four", "date": date(2022, 1, 1), "team": "Australia"}]
    rb = {"A One": {"runs": 1900, "balls": 970, "strike_rate": 195.9}, "B Two": {"runs": 1800, "balls": 1050, "strike_rate": 171.4},
          "C Three": {"runs": 0, "balls": 0, "strike_rate": None}, "D Four": {"runs": 1900, "balls": 1220, "strike_rate": 155.7}}
    c = RP.opposition_card(None, pool, rb, "")
    assert [r["name"] for r in c["payload"]["rows"]] == ["One", "Two", "Four"]
    assert "ahead of Two (171)" in c["title"] and "C Three" in c["help"]


def test_zones_drawn_from_the_batters_side():
    from services.ig_posts.cards import zones_help

    assert "left-hander" in zones_help("LHB") and "right-hander" in zones_help("RHB") and "right-hander" in zones_help(None)
