"""Story-style preview cards (services/preview_cards): titles, sample rules, ordering, formats."""
from datetime import date
from types import SimpleNamespace

from services.preview_cards import build_story
from services.preview_cards.context import GroundMatch, PreviewContext
from services.preview_cards.copy import leader_line, plural, span
from services.preview_cards.spec import Card, CardSpec, Info, SampleRule
from services.preview_cards.stats import wilson, within_noise


def _innings(runs, won, full=True, toss_bat=None, pp=60, mid=80, death=None):
    death = runs - pp - mid if death is None else death
    return {"runs": runs, "wins": int(won), "losses": int(not won), "full_length": int(full),
            "pct_batting_side_won_toss": toss_bat, "powerplay_runs": pp, "middle_runs": mid, "death_runs": death}


def _match(i, year, first_runs, second_runs, chase_won, full=True, no_result=False, toss_chose_field=True):
    first = _innings(first_runs, not chase_won, full, toss_bat=0 if toss_chose_field else 100)
    second = _innings(second_runs, chase_won)
    if no_result:
        first.update(wins=0, losses=0)
    return GroundMatch(id=str(i), year=year, first=first, second=second)


def _ground(n_bat=15, n_chase=13, years=(2022, 2023, 2024, 2025, 2026)):
    out = []
    for i in range(n_bat):
        out.append(_match(i, years[i % len(years)], 190 + i, 170, chase_won=False))
    for i in range(n_chase):
        out.append(_match(100 + i, years[i % len(years)], 180, 200 + i, chase_won=True))
    return out


def _profile(rpo_by_phase, innings=40, spin_share=(0.1, 0.6, 0.1)):
    """An over x bowl_kind profile: `innings` innings, each phase at the given runs per over."""
    rows = []
    for over in range(20):
        ph = 0 if over < 6 else 1 if over < 15 else 2
        spin = round(innings * spin_share[ph])
        for kind, inns in (("spin bowler", spin), ("pace bowler", innings - spin)):
            if inns:
                rows.append({"over": over, "bowl_kind": kind, "innings_count": inns, "balls": 6 * inns,
                             "runs": rpo_by_phase[ph] * inns, "wickets": 0.3 * inns})
    return rows


def _zones(shares, n=1000):
    return [{"wagon_zone": z, "fours": round(n * sh), "sixes": 0} for z, sh in shares.items()]


def _ctx(ground=None, h2h=(1, 4, 0), fmt="T20", par_series=((2024, 189, 7), (2025, 180, 7), (2026, 212, 7)),
         international=False, here=(9, 8, 11), everywhere=(8.5, 8, 10), zones=None, outs=None):
    ctx = PreviewContext(db=None, venue="Wankhede Stadium, Mumbai", team1="Mumbai Indians", team2="Chennai Super Kings",
                         fmt=fmt, start=date(2022, 1, 1), end=date(2026, 10, 4), team1_short="MI", team2_short="CSK")
    history = {
        "h2h_stats": {"team1_wins": h2h[0], "team2_wins": h2h[1], "draws": h2h[2]},
        "venue_results": [{"winner": "MI", "won_batting_first": False}, {"winner": "CSK", "won_batting_first": False},
                          {"winner": "RR", "won_batting_first": True}, {"winner": "-", "won_batting_first": None}],
        "team1_results": [{"winner": "MI"}, {"winner": "MI"}, {"winner": "RCB"}],
        "team2_results": [{"winner": "CSK"}, {"winner": "KKR"}, {"winner": "KKR"}],
    }
    primer = None
    if par_series:
        primer = {"competition": "T20Is" if international else "IPL", "where": "in India" if international else "here",
                  "international": international,
                  "series": [{"year": y, "par": p, "n": n} for y, p, n in par_series]}
    # cached_property values can be preset on the instance.
    ctx.__dict__.update(
        history=history, primer_par=primer if fmt == "T20" else None,
        ground_matches=_ground() if ground is None else ground,
        scope={"leagues": ["IPL"], "include_international": True, "top_teams": 20},
        main_competition="IPL", comparison_scope={"label": "IPL", "filters": {"leagues": ["IPL"]}},
        over_profile={"ground": _profile(here), "all": _profile(everywhere, innings=400)},
        ground_zones=zones or [], ground_dismissals=outs or [],
    )
    return ctx


def _cards(story):
    return {c["id"]: c for ch in story["chapters"] for c in ch["cards"]}


def test_titles_state_the_finding():
    cards = _cards(build_story(_ctx()))
    assert cards["par"]["title"] == "Par here is about 212"
    assert cards["par"]["payload"]["caption"] == "Up from 189 in 2024."
    assert cards["results"]["title"] == "Batting first is no clear edge here: 15 of 28 won"
    assert cards["winning-phases"]["title"] == "Winning sides here cut loose at the death"
    assert cards["totals"]["title"] == "Nobody has posted 210 here since 2023"
    assert cards["glance"]["title"] == "Par about 212, no clear edge for batting first"
    assert cards["head-to-head"]["title"] == "CSK lead 4–1 in their last 5 meetings"
    assert cards["form"]["title"] == "MI come in with 2 wins from their last 5"
    # A no-result counts towards neither side, and the title counts all the matches shown.
    assert cards["recent-results"]["title"] == "Chasing sides won 2 of the last 4 here"


def test_ground_cards_count_the_same_matches():
    cards = _cards(build_story(_ctx()))
    assert cards["results"]["payload"]["decided"] == 28
    assert len(cards["totals"]["payload"]["points"]) == 28
    assert cards["winning-phases"]["n"] == 28
    assert cards["results"]["sample"] == "28 decided matches at Wankhede Stadium · 2022–26"


def test_rain_shortened_and_no_result_matches():
    ground = _ground() + [_match(900, 2026, 90, 91, chase_won=True, full=False),
                          _match(901, 2026, 120, 0, chase_won=False, no_result=True)]
    cards = _cards(build_story(_ctx(ground=ground)))
    assert cards["results"]["payload"]["decided"] == 29       # the rain-cut chase still has a winner
    totals = [p["total"] for p in cards["totals"]["payload"]["points"]]
    assert 90 not in totals and len(totals) == 28  # a 90 in 8 overs is no benchmark; the no-result has no result


def test_chase_record_carries_its_likely_range():
    lo, hi = wilson(32, 59)
    assert (round(lo * 100), round(hi * 100)) == (42, 66)  # the audit's Wankhede figure
    assert within_noise(32, 59) and not within_noise(45, 59)
    card = _cards(build_story(_ctx(ground=_ground(n_bat=5, n_chase=25))))["results"]
    assert card["title"] == "Chasing sides win more here: 25 of 30"
    assert not card["payload"]["within_noise"]
    assert card["payload"]["notes"] == ["Since 2025: chasing sides won 10 of 12.",
                                        "Toss winners chose to chase 30 of 30 times."]


def test_thin_ground_keeps_par_but_drops_ground_records():
    cards = _cards(build_story(_ctx(ground=_ground(n_bat=4, n_chase=3))))
    assert "results" not in cards and "totals" not in cards and "winning-phases" not in cards
    assert "par" in cards and not cards["par"]["small_sample"]  # Primer par is shrunk, not raw
    assert "head-to-head" in cards


def test_international_par_is_by_country():
    cards = _cards(build_story(_ctx(international=True)))
    assert cards["par"]["title"] == "Par for a T20I in India is about 212"
    assert cards["par"]["sample"] == "T20Is in India · 2026 · T20 Primer par"


def test_odi_par_is_the_average_complete_first_innings():
    cards = _cards(build_story(_ctx(fmt="ODI")))
    assert cards["par"]["title"].startswith("Par here is about ")
    assert cards["par"]["sample"] == "28 complete first innings at Wankhede Stadium · 2022–26"


def test_only_meeting_copy():
    assert _cards(build_story(_ctx(h2h=(1, 0, 0))))["head-to-head"]["title"] == "MI won their only meeting"
    assert _cards(build_story(_ctx(h2h=(0, 0, 1))))["head-to-head"]["title"] == "Their only meeting had no winner"


def test_chapters_keep_their_order_and_cards_rank_inside():
    story = build_story(_ctx())
    assert [c["id"] for c in story["chapters"]] == ["glance", "ground", "teams"]
    ground = [c["relevance"] for c in story["chapters"][1]["cards"]]
    assert ground == sorted(ground, reverse=True)


def test_data_links_carry_the_cards_scope():
    url = _cards(build_story(_ctx()))["results"]["query_url"]
    assert url.startswith("https://hindsightcricket.com/query?")
    assert "query_mode=team_innings" in url
    assert "leagues=IPL" in url and "include_international=true" in url and "top_teams=20" in url


def test_format_and_failure_handling():
    def boom(ctx):
        raise RuntimeError("nope")

    t20_only = CardSpec("x", "ground", "?", lambda ctx: Card("x", "ground", "stat", "t", "s", {}, 50, Info("w")),
                        formats=("T20",))
    story = build_story(_ctx(fmt="ODI"), registry=[t20_only, CardSpec("b", "ground", "?", boom)])
    assert story["chapters"] == []  # T20-only card skipped for ODI; the failing card left out


def test_copy_helpers():
    assert plural(1, "match") == "1 match" and plural(3, "match") == "3 matches"
    assert plural(2, "decided match") == "2 decided matches" and plural(5, "complete first innings").endswith("innings")
    assert span(date(2022, 1, 1), date(2026, 10, 4)) == "2022–26"
    assert leader_line("MI", 2, "CSK", 2) == ("Level at 2–2", None)
    assert leader_line("MI", 1, "CSK", 4) == ("CSK lead 4–1", "CSK")


def test_sample_rule_hides_below_floor():
    spec = CardSpec("x", "ground", "?", lambda ctx: Card("x", "ground", "stat", "t", "s", {}, 2, Info("w")),
                    sample=SampleRule(hide_below=3))
    assert spec.make(SimpleNamespace(fmt="T20")) is None


def test_totals_falls_back_to_benchmarks_on_a_thinner_ground():
    cards = _cards(build_story(_ctx(ground=_ground(n_bat=8, n_chase=7))))
    assert cards["totals"]["visual"] == "benchmarks"
    assert cards["totals"]["title"] == "190 has been defended here, and 206 chased"


def test_ground_against_its_competition():
    cards = _cards(build_story(_ctx()))
    shape = cards["innings-shape"]
    # +0.5 an over for 6 overs, level for 9, +1 for 5: 8 runs ahead after 20.
    assert shape["title"] == "An innings here is about 8 runs ahead of the IPL by the 20th over"
    assert shape["payload"]["here"][-1] - shape["payload"]["all"][-1] == 8
    assert shape["sample"] == "40 innings at Wankhede Stadium v all IPL grounds · 2022–26"
    assert cards["phases"]["title"] == "Runs come faster here in the death overs (+1.0 an over)"
    assert cards["pace-spin"]["title"] == "Spin bowls 60% of the middle overs here, about the IPL norm"


def test_innings_count_adds_pace_and_spin_rows():
    # Same run rate everywhere, different pace/spin split: the worm must not move.
    ctx = _ctx()
    ctx.__dict__["over_profile"] = {"ground": _profile((8, 8, 8), spin_share=(0.5, 0.5, 0.5)),
                                    "all": _profile((8, 8, 8), innings=400, spin_share=(0.1, 0.1, 0.1))}
    shape = _cards(build_story(ctx))["innings-shape"]
    assert shape["payload"]["here"] == shape["payload"]["all"]
    assert shape["title"] == "An innings here tracks the IPL average, over by over"


def test_boundary_zones_only_where_the_ground_differs():
    from services.preview_cards.ground import BASELINES
    usual = {int(z): sh for z, sh in BASELINES["boundary_zones"]["share"].items()}
    assert "boundary-zones" not in _cards(build_story(_ctx(zones=_zones(usual))))
    skewed = dict(usual)
    skewed[1] += 0.05
    skewed[6] -= 0.05
    card = _cards(build_story(_ctx(zones=_zones(skewed))))["boundary-zones"]
    assert card["title"] == "Fine leg gets 1.6× its usual share of boundaries here"
    assert "Boundaries" in [t["label"] for t in _cards(build_story(_ctx(zones=_zones(skewed))))["glance"]["payload"]["tiles"]]


def test_dismissals_need_a_real_gap_not_just_significance():
    from services.preview_cards.ground import BASELINES
    usual = BASELINES["dismissals"]["share"]

    def outs(shares, n=4000):
        raw = {"caught": "caught", "bowled": "bowled", "lbw": "leg before wicket", "other": "stumped"}
        return [{"dismissal": raw[k], "wickets": round(n * v)} for k, v in shares.items()]

    # "other" 3.2% -> 4.4%: significant on 4,000 wickets, 1.4x, but only 1.2 points: no card.
    small = {**usual, "other": usual["other"] + 0.012, "caught": usual["caught"] - 0.012}
    assert "dismissals" not in _cards(build_story(_ctx(outs=outs(small))))
    big = {**usual, "lbw": usual["lbw"] + 0.05, "caught": usual["caught"] - 0.05}
    card = _cards(build_story(_ctx(outs=outs(big))))["dismissals"]
    assert card["title"] == "Batters are lbw 1.7× as often as usual here"


def test_glance_tiles_come_from_the_cards():
    cards = _cards(build_story(_ctx()))
    tiles = {t["label"]: t for t in cards["glance"]["payload"]["tiles"]}
    assert tiles["Par"]["value"] == "212" and tiles["Par"]["card"] == "par"
    assert tiles["Chasing"]["value"] == "13/28" and tiles["Chasing"]["card"] == "results"
    assert tiles["Head to head"]["value"] == "4–1" and tiles["Head to head"]["sub"] == "CSK lead"
    assert tiles["MI form"]["value"] == "2/3"
    assert len(tiles) <= 6
    assert story_first(build_story(_ctx())) == "glance"


def story_first(story):
    return story["chapters"][0]["cards"][0]["id"]


# --- the teams (chunk 6) ------------------------------------------------------------------------

TEAMS10 = ["Mumbai Indians", "Chennai Super Kings", *[f"Side {i}" for i in range(8)]]


def _team_ctx(mi_bat=(10, 5, 0), csk_bat=(0, 0, 0), mi_bowl=(0, 0, 0), csk_bowl=(0, 0, -12),
              elo=((1500, 1520, 1540), (1500, 1490, 1480)), meeting=None):
    ctx = _ctx()
    phases = ("powerplay", "middle", "death")

    def rows(side_col, values_for):
        out = []
        for team in TEAMS10:
            for k, ph in enumerate(phases):
                out.append({side_col: team, "phase": ph, "balls": 600, "innings_count": 28,
                            "raa_per_100": values_for(team, k), "runs": 800})
        return out

    def bat(team, k):
        return {"Mumbai Indians": mi_bat, "Chennai Super Kings": csk_bat}.get(team, (2, 2, 2))[k] + 20
    def bowl(team, k):
        return {"Mumbai Indians": mi_bowl, "Chennai Super Kings": csk_bowl}.get(team, (0, 0, 0))[k] - 10

    ctx.__dict__.update(
        team_names={"MI": ["Mumbai Indians"], "CSK": ["Chennai Super Kings"]},
        team_window={"label": "IPL", "start": date(2025, 1, 1), "end": date(2026, 10, 4),
                     "args": {"leagues": ["IPL"], "start_date": date(2025, 1, 1), "end_date": date(2026, 10, 4),
                              "fmt": "T20", "gender": "male"}},
        team_phases={"bat": rows("batting_team", bat), "bowl": rows("bowling_team", bowl)},
        fixture_competition="IPL",
        elo_series={"MI": [{"date": f"2026-04-0{i + 1}", "elo": e, "won": True} for i, e in enumerate(elo[0])],
                    "CSK": [{"date": f"2026-04-0{i + 1}", "elo": e, "won": False} for i, e in enumerate(elo[1])]},
        last_meeting=meeting, last_xis={},
    )
    return ctx


def test_where_won_is_centred_on_the_competition():
    card = _cards(build_story(_team_ctx()))["where-won"]
    # Raw RAA carries +20 batting / -10 bowling for every IPL side; centring removes it.
    rows = {(r["group"], r["phase"]): r for r in card["payload"]["rows"]}
    assert abs(rows[("Batting", "death")]["team1"] - rows[("Batting", "death")]["team2"]) < 1e-9
    assert rows[("Bowling", "middle")]["team1"] > -2  # an average bowling side sits near 0, not -10
    # CSK's death bowling is 12 worse than average and MI's is average: MI hold the edge.
    assert card["title"] == "MI death bowling is the biggest edge: 12 runs per 100 balls"


def test_phase_strength_names_the_most_extreme_rank():
    card = _cards(build_story(_team_ctx()))["phase-strength"]
    # MI's powerplay batting (1st) and CSK's death bowling (10th) are equally extreme; the first wins.
    assert card["title"] == "MI powerplay batting ranks 1st of 10"


def test_rating_titles():
    assert _cards(build_story(_team_ctx()))["rating"]["title"] == "MI come in rated higher: 1540 to CSK's 1480"
    even = _cards(build_story(_team_ctx(elo=((1500, 1500, 1460), (1500, 1500, 1465)))))["rating"]
    assert even["title"] == "Evenly rated: MI 1460, CSK 1465"


def test_last_meeting_titles():
    def meeting(winner, first, second):
        return {"id": "1", "date": date(2026, 5, 2), "venue": "MA Chidambaram Stadium, Chepauk", "competition": "IPL",
                "winner": winner, "path": [],
                "innings": [{"innings": 1, "side": first[0], "runs": first[1], "wickets": first[2], "balls": 120},
                            {"innings": 2, "side": second[0], "runs": second[1], "wickets": second[2], "balls": 109}]}
    chased = _cards(build_story(_team_ctx(meeting=meeting("CSK", ("MI", 159, 7), ("CSK", 160, 2)))))["last-meeting"]
    assert chased["title"] == "Last time: CSK chased 160 with 8 wickets in hand"
    assert chased["help"] is None  # no ball-by-ball path, no "chance of winning" line
    defended = _cards(build_story(_team_ctx(meeting=meeting("MI", ("MI", 180, 6), ("CSK", 179, 9)))))["last-meeting"]
    assert defended["title"] == "Last time: MI defended 180 and won by 1 run"
    washout = _cards(build_story(_team_ctx(meeting=meeting(None, ("MI", 60, 1), ("CSK", 0, 0)))))["last-meeting"]
    assert washout["title"] == "Last time: no result"


# --- the players (chunk 7) ----------------------------------------------------------------------

def _players_ctx(monkeypatch, responses):
    """A context whose query-builder calls answer from `responses`, keyed by group_by."""
    from services.preview_cards import players as P

    def fake_run(ctx, args):
        return responses.get(tuple(args["group_by"]), [])
    monkeypatch.setattr(P, "_run", fake_run)
    ctx = _team_ctx()
    ctx.__dict__["last_xis"] = {
        "MI": {"date": date(2026, 5, 1), "opponent": "RR", "players": ["SK Yadav", "JJ Bumrah", "HH Pandya"]},
        "CSK": {"date": date(2026, 5, 1), "opponent": "GT", "players": ["N Ahmad", "S Samson", "K Ahmed"]},
    }
    return ctx


def test_key_battles_shrink_small_samples_and_skip_teammates(monkeypatch):
    from services.preview_cards import players as P
    pairs = [
        # 37 balls, raw edge +40 over expected: likely edge 40 * 37/157 = 9.4
        {"batter": "SK Yadav", "bowler": "N Ahmad", "balls": 37, "runs": 61, "wickets": 1, "raa_per_100": 50.0},
        # 20 balls, raw +20: likely 20 * 20/140 = 2.9, below the 5-run floor
        {"batter": "HH Pandya", "bowler": "K Ahmed", "balls": 20, "runs": 30, "wickets": 0, "raa_per_100": 30.0},
        # teammates are never a battle
        {"batter": "SK Yadav", "bowler": "JJ Bumrah", "balls": 60, "runs": 20, "wickets": 4, "raa_per_100": -80.0},
        # bowler ahead: raw -60 over 50 balls -> likely -17.6
        {"batter": "S Samson", "bowler": "JJ Bumrah", "balls": 50, "runs": 40, "wickets": 3, "raa_per_100": -50.0},
    ]
    bat = [{"batter": n, "raa_per_100": 10.0} for n in ("SK Yadav", "HH Pandya", "S Samson")]
    bowl = [{"bowler": n, "raa_per_100": 0.0} for n in ("N Ahmad", "K Ahmed", "JJ Bumrah")]
    ctx = _players_ctx(monkeypatch, {("batter", "bowler"): pairs, ("batter",): bat, ("bowler",): bowl})
    rows = P.battles(ctx)
    assert [(r["batter"], r["bowler"], r["edge"]) for r in rows] == [("S Samson", "JJ Bumrah", -18), ("SK Yadav", "N Ahmad", 9)]
    card = P.key_battles(ctx)
    assert card.title == "JJ Bumrah has the edge on S Samson: 40 off 50, out 3 times"


def test_milestones_bands_and_wording():
    from services.milestones import within_reach
    totals = {"DL Chahar": {"runs": 142, "sixes": 9, "wickets": 96, "matches": 103},
              "HH Pandya": {"runs": 2955, "sixes": 160, "wickets": 70, "matches": 149},
              "Far": {"runs": 2900, "sixes": 120, "wickets": 40, "matches": 80}}
    found = within_reach(totals, {"DL Chahar": "CSK", "HH Pandya": "MI", "Far": "MI"}, "T20")
    texts = [f"{m.player} {m.phrase('IPL')}" for m in found]
    assert "DL Chahar is 4 wickets from 100 IPL wickets" in texts
    assert "HH Pandya is 45 runs from 3,000 IPL runs" in texts
    assert "HH Pandya would play a 150th IPL match" in texts
    assert not any(t.startswith("Far") for t in texts)
    assert all(" his " not in t and " her " not in t for t in texts)


def test_how_they_bowl_needs_600_balls(monkeypatch):
    from services.preview_cards import players as P
    def grid(bowler, n, extra_cell="SHORT"):
        rows = [{"bowler": bowler, "line": "OUTSIDE_OFFSTUMP", "length": "GOOD_LENGTH", "balls": n // 2},
                {"bowler": bowler, "line": "ON_THE_STUMPS", "length": extra_cell, "balls": n - n // 2}]
        return rows
    thin = _players_ctx(monkeypatch, {("bowler", "line", "length"): grid("JJ Bumrah", 500)})
    assert P.how_they_bowl(thin) is None
    full = _players_ctx(monkeypatch, {("bowler", "line", "length"): grid("JJ Bumrah", 900, "YORKER")})
    card = P.how_they_bowl(full)
    assert card.title.startswith("JJ Bumrah bowls yorkers on the stumps")
    assert card.payload["side"] == "MI"
