from services.ig_posts import spotlight as S


def row(balls, impact100, raa100):
    return {"balls": balls, "impact_per_100": impact100, "raa_per_100": raa100}


def test_per_over_and_the_cell_floor():
    assert round(S.per_over(row(204, 101.83, 15.77), "raa"), 2) == 0.95  # Bhuvneshwar, 2026 powerplay
    assert round(S.per_over(row(204, 101.83, 15.77), "impact"), 2) == 6.11
    assert S.per_over(row(29, 50, 10), "impact") is None  # under 30 balls: no number


def test_short_names_avoid_shared_surnames():
    assert S.short_name("Bhuvneshwar Kumar") == "Bhuvneshwar"
    assert S.short_name("Mukesh Kumar") == "Mukesh"
    assert S.short_name("Arshdeep Singh") == "Arshdeep"
    assert S.short_name("Jasprit Bumrah") == "Bumrah"


def test_heat_table_ranks_within_each_year_and_rings_the_best():
    table = {"A": {"2025": 1.0, "2026": None}, "B": {"2025": 2.0, "2026": 0.5}, "C": {"2025": 0.0, "2026": 1.5}}
    out = S.heat(table, ["2025", "2026"], "A", ["A", "B", "C"])
    rows = {r["name"]: r for r in out["rows"]}
    assert rows["B"]["pct"]["2025"] == 100 and rows["C"]["pct"]["2025"] == 0
    assert rows["A"]["pct"]["2026"] is None and rows["A"]["highlight"]
    assert rows["B"]["leader"] == ["2025"] and rows["C"]["leader"] == ["2026"]


def test_peer_title_written_from_the_numbers():
    spec = {"player": "Bhuvneshwar Kumar", "years": [2025, 2026]}
    data = {}
    vals = {"Bhuvneshwar Kumar": 0.95, "Jasprit Bumrah": 1.56, "Arshdeep Singh": -0.32, "Mukesh Kumar": -1.57}
    for b, v in vals.items():
        for y in (2025, 2026):
            data[(b, y, "powerplay")] = row(100, 0, v * 100 / 6)
    c = S.peer_card(spec, data, list(vals), "powerplay", "raa")
    assert c["title"] == "In 2026, only Bumrah beat Bhuvneshwar's powerplay runs saved (+0.9 per over)"
    assert [r["short"] for r in c["payload"]["rows"]][0] == "Bhuvneshwar"


def test_spotlight_deeper_cut_is_about_the_player(monkeypatch):
    from services.ig_posts import deep_cut

    monkeypatch.setattr(deep_cut, "resolve", lambda db, n: ("B Kumar", "Bhuvneshwar Kumar"))
    people, _scope, label = deep_cut.subjects_for(None, {"kind": "spotlight", "subject": "Bhuvneshwar Kumar",
                                                         "subject_role": "bowler", "title": "x"})
    assert people == [("bowler", "B Kumar", "Bhuvneshwar Kumar")] and label.startswith("T20s since")


def test_spotlight_can_set_the_deeper_cut_window(monkeypatch):
    from services.ig_posts import deep_cut

    monkeypatch.setattr(deep_cut, "resolve", lambda db, n: ("B Kumar", "Bhuvneshwar Kumar"))
    fact = {"kind": "spotlight", "subject": "Bhuvneshwar Kumar", "subject_role": "bowler", "title": "x",
            "deep_cut_scope": {"since": 2026, "over_max": 5, "label": "T20 powerplays in 2026"}}
    _people, scope, label = deep_cut.subjects_for(None, fact)
    assert scope["over_max"] == 5 and scope["start_date"].year == 2026 and label == "T20 powerplays in 2026"
