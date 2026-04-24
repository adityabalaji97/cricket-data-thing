from datetime import date
from unittest.mock import MagicMock

from services import query_builder_v2 as qb


def test_pre_2015_bowl_kind_routes_to_legacy_only():
    routing = qb.analyze_query_requirements(
        start_date=date(2008, 1, 1),
        end_date=date(2014, 12, 31),
        group_by=[],
        filters_used={"bowl_kind": ["spin bowler"]},
    )
    assert routing["use_legacy"] is True
    assert routing["use_new"] is False
    assert any("inferred" in warning.lower() for warning in routing["warnings"])


def test_mixed_date_range_with_bowl_kind_uses_both_tables():
    routing = qb.analyze_query_requirements(
        start_date=date(2012, 1, 1),
        end_date=date(2019, 12, 31),
        group_by=[],
        filters_used={"bowl_kind": ["spin bowler"]},
    )
    assert routing["use_legacy"] is True
    assert routing["use_new"] is True


def test_mixed_date_range_with_bowl_style_uses_both_tables():
    routing = qb.analyze_query_requirements(
        start_date=date(2012, 1, 1),
        end_date=date(2019, 12, 31),
        group_by=[],
        filters_used={"bowl_style": ["OB"]},
    )
    assert routing["use_legacy"] is True
    assert routing["use_new"] is True


def test_legacy_where_clause_supports_bowl_style_and_bowl_kind_filters():
    where_clause, params = qb.build_legacy_where_clause(
        venue=None,
        start_date=date(2008, 1, 1),
        end_date=date(2014, 12, 31),
        leagues=[],
        teams=[],
        batting_teams=[],
        bowling_teams=[],
        players=[],
        batters=[],
        bowlers=[],
        bowl_style=[" ob "],
        bowl_kind=["Spin Bowler"],
        crease_combo=[],
        dismissal=[],
        innings=None,
        over_min=None,
        over_max=None,
        match_outcome=[],
        is_chase=None,
        chase_outcome=[],
        toss_decision=[],
        include_international=False,
        top_teams=None,
        group_by=[],
        base_params={"limit": 100, "offset": 0},
        db=None,
    )

    assert "d.bowler_type" in where_clause
    assert "p.bowler_type" in where_clause
    assert "ANY(:bowl_style)" in where_clause
    assert "ANY(:bowl_kind)" in where_clause
    assert params["bowl_style"] == ["OB"]
    assert params["bowl_kind"] == ["spin bowler"]


def test_legacy_grouping_map_uses_derived_bowl_fields():
    grouping_map = qb.get_legacy_grouping_columns_map()
    assert grouping_map["bowl_style"] != "NULL"
    assert grouping_map["bowl_kind"] != "NULL"
    assert "mixture/unknown" in grouping_map["bowl_kind"]


def test_legacy_only_service_response_normalizes_alias_names(monkeypatch):
    monkeypatch.setattr(
        qb,
        "analyze_query_requirements",
        lambda **_: {
            "use_legacy": True,
            "use_new": False,
            "advanced_columns_used": set(),
            "warnings": [],
            "legacy_date_range": (date(2008, 1, 1), date(2014, 12, 31)),
            "new_date_range": None,
        },
    )
    monkeypatch.setattr(qb, "build_legacy_where_clause", lambda **_: ("WHERE 1=1", {"limit": 100, "offset": 0}))
    monkeypatch.setattr(qb, "get_legacy_total_balls", lambda *_: 1)
    monkeypatch.setattr(
        qb,
        "query_legacy_ungrouped",
        lambda *_: (
            [
                {
                    "match_id": "m1",
                    "innings": 2,
                    "over": 1,
                    "ball": 1,
                    "batter": "SP Narine",
                    "bowler": "Harbhajan Singh",
                    "runs_off_bat": 0,
                    "total_runs": 0,
                    "batting_team": "KKR",
                    "bowling_team": "MI",
                    "bat_hand": None,
                    "bowl_style": "OB",
                    "bowl_kind": "spin bowler",
                    "crease_combo": "lhb_rhb",
                    "line": None,
                    "length": None,
                    "shot": None,
                    "control": None,
                    "wagon_x": None,
                    "wagon_y": None,
                    "wagon_zone": None,
                    "wicket_type": None,
                    "venue": "Wankhede Stadium, Mumbai",
                    "date": "2011-05-22",
                    "competition": "Indian Premier League",
                    "year": 2011,
                    "outcome": None,
                }
            ],
            1,
        ),
    )
    monkeypatch.setattr(qb, "load_player_aliases_for_merge", lambda *_: {"SP Narine": "Sunil Narine"})

    db = MagicMock()
    db.execute.return_value.scalar.return_value = 1

    response = qb.query_deliveries_service(
        venue=None,
        start_date=date(2008, 1, 1),
        end_date=date(2014, 12, 31),
        leagues=["IPL"],
        teams=[],
        batting_teams=[],
        bowling_teams=[],
        players=[],
        batters=[],
        bowlers=[],
        bat_hand=None,
        bowl_style=[],
        bowl_kind=["spin bowler"],
        crease_combo=[],
        line=[],
        length=[],
        shot=[],
        control=None,
        wagon_zone=[],
        dismissal=[],
        innings=2,
        over_min=None,
        over_max=None,
        match_outcome=[],
        is_chase=None,
        chase_outcome=[],
        toss_decision=[],
        group_by=[],
        show_summary_rows=False,
        min_balls=None,
        max_balls=None,
        min_runs=None,
        max_runs=None,
        min_wickets=None,
        max_wickets=None,
        limit=100,
        offset=0,
        include_international=False,
        top_teams=None,
        query_mode="delivery",
        db=db,
    )

    assert response["data"][0]["batter"] == "Sunil Narine"
