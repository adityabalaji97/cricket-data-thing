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


def test_accuracy_card_ranks_good_length_and_flips_short(monkeypatch):
    def q(db, **args):
        if args["group_by"] == ["bowler", "length"]:
            rows = []
            for b, good, short, other in (("Bhuvneshwar Kumar", 408, 14, 376), ("Mohammed Siraj", 426, 78, 486),
                                          ("Harshit Rana", 145, 54, 221), ("Arshdeep Singh", 614, 135, 767)):
                rows += [{"bowler": b, "length": "GOOD_LENGTH", "balls": good}, {"bowler": b, "length": "SHORT", "balls": short},
                         {"bowler": b, "length": "FULL", "balls": other}]
            return rows
        rows = []
        for b, false, ok in (("Bhuvneshwar Kumar", 231, 565), ("Mohammed Siraj", 328, 659), ("Harshit Rana", 157, 263),
                             ("Arshdeep Singh", 457, 1056)):
            rows += [{"bowler": b, "control": 0, "balls": false}, {"bowler": b, "control": 1, "balls": ok}]
        return rows
    monkeypatch.setattr(S, "_q", q)
    spec = {"player": "Bhuvneshwar Kumar", "years": [2023]}
    c = S.accuracy_card(None, spec, ["Bhuvneshwar Kumar", "Mohammed Siraj", "Harshit Rana", "Arshdeep Singh"])
    assert c["kicker"] == "The deeper cut"
    assert c["title"] == "Bhuvneshwar lands 51% of his new balls on a good length, more than any India pacer"
    rows = {r["name"]: r for r in c["payload"]["rows"]}
    assert rows["Bhuvneshwar Kumar"]["pct"]["Short"] == 100 and "Short" in rows["Bhuvneshwar Kumar"]["leader"]
    assert c["help"].startswith("Accuracy, not menace: ") and "Rana" in c["help"]


def test_case_odi_external_figures_must_be_confirmed():
    import pytest
    from services.ig_posts import case_odi

    spec = {"external": {"heading": "From elsewhere", "lines": ["15 wickets"], "source": "ESPNcricinfo", "confirmed": False}}
    with pytest.raises(ValueError):
        case_odi.external_slide(spec)
    spec["external"]["confirmed"] = True
    assert case_odi.external_slide(spec)["body"].endswith("Source: ESPNcricinfo (not Hindsight data)")


def test_case_odi_phase_card_flips_shading_and_claims_only_what_it_leads():
    from datetime import date

    from services.ig_posts import case_odi

    spec = {"player": "Mohammad Shami", "since": date(2019, 1, 1)}
    def cell(bpw):
        return {"bpw": bpw, "econ": 6.0, "balls": 300, "wickets": 20}
    phases = {"Mohammad Shami": {"New ball": cell(39), "Middle": cell(23), "Death": cell(14)},
              "Harshit Rana": {"New ball": cell(39), "Middle": cell(22), "Death": {"bpw": None, "econ": None}},
              "Jasprit Bumrah": {"New ball": cell(47), "Middle": cell(39), "Death": cell(21)},
              "Arshdeep Singh": {"New ball": cell(26), "Middle": cell(49), "Death": cell(30)}}
    c = case_odi.phase_card(spec, phases, list(phases), "bpw")
    assert c["title"] == "No India pacer takes ODI wickets at the death as often as Shami"  # Rana leads the middle
    rows = {r["name"]: r for r in c["payload"]["rows"]}
    assert rows["Mohammad Shami"]["pct"]["Death"] == 100 and "Death" in rows["Mohammad Shami"]["leader"]
    assert rows["Arshdeep Singh"]["leader"] == ["New ball"]
