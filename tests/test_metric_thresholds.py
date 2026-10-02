import pytest

from services.metric_thresholds import ThresholdError, describe, parse, row_passes, sql_conditions


def test_parse_supported_and_warns_on_known_unsupported():
    thresholds, warnings = parse(["average:gte:50", "control_percentage:gte:80", "economy:lte:7"])
    assert thresholds == [("average", "gte", 50.0), ("control_percentage", "gte", 80.0)]
    assert len(warnings) == 1 and "economy" in warnings[0]


def test_needs_and_applicable():
    from services.metric_thresholds import applicable, needs
    t = [("average", "gte", 40.0), ("control_percentage", "gte", 80.0), ("impact_per_100", "gte", 10.0)]
    assert needs(t) == {"control", "metrics"}
    kept, warns = applicable(t, primer_available=False, cumulative=False)
    assert [m for m, _, _ in kept] == ["average", "control_percentage"] and "men's T20" in warns[0]
    kept, warns = applicable(t, primer_available=True, cumulative=True)
    assert [m for m, _, _ in kept] == ["average"] and len(warns) == 2


def test_row_passes_stage2_metrics_read_reported_columns():
    t = [("control_percentage", "gte", 80.0), ("impact_per_100", "gte", 10.0)]
    assert row_passes({"control_percentage": 82.0, "impact_per_100": 12.5}, t)
    assert not row_passes({"control_percentage": 82.0, "impact_per_100": None}, t)


@pytest.mark.parametrize("bad", ["average:>=:50", "average:gte", "average:gte:fifty", "avg:gte:50"])
def test_parse_rejects_malformed(bad):
    with pytest.raises(ThresholdError):
        parse([bad])


def test_sql_conditions_bind_values():
    params = {}
    conds = sql_conditions([("average", "gte", 50.0), ("strike_rate", "lt", 120.0)], params)
    assert conds[0].endswith(">= :thr_0") and conds[1].endswith("< :thr_1")
    assert params == {"thr_0": 50.0, "thr_1": 120.0}


def test_row_passes_matches_reported_definitions():
    t = [("average", "gte", 50.0), ("strike_rate", "gte", 100.0)]
    assert row_passes({"runs": 600, "balls": 500, "wickets": 10}, t)       # avg 60, SR 120
    assert not row_passes({"runs": 450, "balls": 500, "wickets": 10}, t)   # SR 90
    # No dismissals: no average, so an average threshold is not met (the table shows no value).
    assert not row_passes({"runs": 600, "balls": 500, "wickets": 0}, t)


def test_describe():
    assert describe([("strike_rate", "gte", 100.0)]) == ["strike rate >= 100"]
