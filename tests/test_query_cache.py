from datetime import date

import pytest

from services import query_cache, snapshots


def test_equal_queries_get_equal_keys_whatever_the_order_or_empties():
    a = {"batters": ["V Kohli", "RG Sharma"], "start_date": date(2024, 1, 1), "leagues": [], "venue": None,
         "group_by": ["batter", "year"]}
    b = {"group_by": ["batter", "year"], "start_date": "2024-01-01", "batters": ["RG Sharma", "V Kohli"]}
    assert query_cache.cache_key(a, "v1") == query_cache.cache_key(b, "v1")


def test_group_by_order_and_data_version_change_the_key():
    base = {"group_by": ["batter", "year"]}
    assert query_cache.cache_key(base, "v1") != query_cache.cache_key({"group_by": ["year", "batter"]}, "v1")
    assert query_cache.cache_key(base, "v1") != query_cache.cache_key(base, "v2")


def test_cache_disabled_just_runs(monkeypatch):
    monkeypatch.setenv("QUERY_CACHE", "0")
    assert query_cache.cached_run(None, {"group_by": ["batter"]}, lambda: {"data": [1]}) == {"data": [1]}


def test_snapshot_params_are_whitelisted_and_normalised():
    params = snapshots._clean_query_params({"format": "ODI", "group_by": "partnership", "batters": "V Kohli",
                                            "start_date": "2019-01-01", "sort_by": "control_percentage"})
    assert params["fmt"] == "ODI" and params["group_by"] == ["partnership"] and params["batters"] == ["V Kohli"]
    assert params["start_date"] == date(2019, 1, 1)
    with pytest.raises(snapshots.SnapshotError):
        snapshots._clean_query_params({"group_by": ["batter"], "drop_table": "x"})
    with pytest.raises(snapshots.SnapshotError):
        snapshots._clean_query_params({"format": "T20"})


def test_snapshot_params_from_site_query_string():
    from services.snapshots import params_from_query_string

    params = params_from_query_string(
        "format=ODI&gender=male&start_date=2019-01-01&group_by=partnership&min_balls=1000"
        "&leagues=IPL,BBL&wagon_zone=1,2&include_international=true&limit=1000&offset=0"
    )
    assert params["format"] == "ODI"
    assert params["group_by"] == ["partnership"]
    assert params["min_balls"] == 1000
    assert params["leagues"] == ["IPL", "BBL"]
    assert params["wagon_zone"] == [1, 2]
    assert params["include_international"] is True
    assert "limit" not in params and "offset" not in params


def test_snapshot_rejects_unknown_query_keys():
    import pytest

    from services.snapshots import SnapshotError, _clean_query_params, params_from_query_string

    with pytest.raises(SnapshotError):
        _clean_query_params(params_from_query_string("group_by=batter&drop_table=1"))


def test_snapshot_default_title_is_a_self_contained_statement():
    from datetime import date

    from services.snapshots import default_title

    title = default_title({"fmt": "ODI", "group_by": ["partnership"], "start_date": date(2019, 1, 1),
                           "min_balls": 1000}, "control_percentage")
    assert title == "ODI partnerships by control %, since 2019 (1,000+ balls)"
    assert default_title({"batters": ["V Kohli"], "leagues": ["IPL"], "group_by": ["phase"]}, "strike_rate") \
        == "V Kohli: IPL phases by strike rate"
