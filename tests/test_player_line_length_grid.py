from routers import player_line_length as pll


class FakeRow:
    def __init__(self, **kwargs):
        self._mapping = kwargs


def test_normalize_bucket_aliases():
    assert pll._normalize_line_bucket("OFF_STUMP") == "OUTSIDE_OFFSTUMP"
    assert pll._normalize_line_bucket("MIDDLE") == "ON_THE_STUMPS"
    assert pll._normalize_length_bucket("SHORT_OF_LENGTH") == "SHORT_OF_A_GOOD_LENGTH"
    assert pll._normalize_length_bucket("FULL_TOSS") == "FULL_TOSS"


def test_rows_to_line_length_agg_merges_normalized_buckets():
    rows = [
        FakeRow(
            line_bucket="OFF_STUMP",
            length_bucket="SHORT_OF_LENGTH",
            balls=10,
            runs=12,
            control_balls=5,
            boundary_balls=2,
            dot_balls=4,
        ),
        FakeRow(
            line_bucket="OUTSIDE_OFFSTUMP",
            length_bucket="SHORT_OF_A_GOOD_LENGTH",
            balls=6,
            runs=10,
            control_balls=3,
            boundary_balls=1,
            dot_balls=2,
        ),
    ]

    cells = pll._rows_to_line_length_agg(rows)
    key = ("OUTSIDE_OFFSTUMP", "SHORT_OF_A_GOOD_LENGTH")

    assert key in cells
    assert cells[key]["balls"] == 16.0
    assert cells[key]["runs"] == 22.0
    assert cells[key]["control_balls"] == 8.0
    assert cells[key]["boundary_balls"] == 3.0
    assert cells[key]["dot_balls"] == 6.0


def test_build_line_length_grid_returns_metrics_and_deltas():
    player_cells = {
        ("OUTSIDE_OFFSTUMP", "GOOD_LENGTH"): {
            "balls": 20.0,
            "runs": 30.0,
            "control_balls": 12.0,
            "boundary_balls": 4.0,
            "dot_balls": 8.0,
        }
    }
    global_cells = {
        ("OUTSIDE_OFFSTUMP", "GOOD_LENGTH"): {
            "balls": 40.0,
            "runs": 40.0,
            "control_balls": 20.0,
            "boundary_balls": 6.0,
            "dot_balls": 20.0,
        }
    }

    grid = pll._build_line_length_grid(
        player_cells=player_cells,
        global_cells=global_cells,
        similar_cells={},
        bowl_kind_cells={},
        bowl_style_cells={},
    )

    assert grid["line_order"] == pll.LINE_ORDER
    assert grid["length_order"] == pll.LENGTH_ORDER

    key = "GOOD_LENGTH_OUTSIDE_OFFSTUMP"
    cell = grid["cells"][key]

    assert cell["player"]["balls"] == 20
    assert cell["player"]["strike_rate"] == 150.0
    assert cell["player"]["control_pct"] == 60.0
    assert cell["player"]["boundary_pct"] == 20.0
    assert cell["player"]["dot_pct"] == 40.0

    assert cell["global_avg"]["strike_rate"] == 100.0
    assert cell["global_avg"]["control_pct"] == 50.0
    assert cell["global_avg"]["boundary_pct"] == 15.0
    assert cell["global_avg"]["dot_pct"] == 50.0

    assert cell["deltas"]["global_avg"]["strike_rate"] == 50.0
    assert cell["deltas"]["global_avg"]["control_pct"] == 10.0
    assert cell["deltas"]["global_avg"]["boundary_pct"] == 5.0
    assert cell["deltas"]["global_avg"]["dot_pct"] == -10.0

    empty_key = "FULL_TOSS_WIDE_DOWN_LEG"
    empty_cell = grid["cells"][empty_key]
    assert empty_cell["player"] is None
    assert empty_cell["global_avg"] is None
    assert empty_cell["deltas"]["global_avg"] is None
