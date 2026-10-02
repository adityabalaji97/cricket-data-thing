from services import pack_charts
from services.pack_charts import rank_forms, scatter_axes, valid_forms


def test_valid_forms_follow_data_shape():
    assert valid_forms({"group_by": ["batter"], "rows": 366, "has_subject": True}) == ["bars", "stat"]
    assert valid_forms({"group_by": ["year"], "rows": 7}) == ["line", "bars"]
    assert valid_forms({"group_by": ["year"], "rows": 2}) == ["bars"]  # too few seasons for a trend
    shape = {"group_by": ["batter"], "rows": 134, "has_subject": True, "scatter": ("strike_rate", "average")}
    assert valid_forms(shape) == ["scatter", "bars", "stat"]
    shape["rows"] = 5  # a scatter of five dots says nothing
    assert valid_forms(shape) == ["bars", "stat"]


def test_scatter_only_when_question_names_two_metrics():
    rows = [{"average": 40.0, "strike_rate": 150.0, "control_percentage": 80.0}]
    assert scatter_axes({"type": "scatter", "x_axis": "strike_rate", "y_axis": "average"}, "average", rows) == ("strike_rate", "average")
    assert scatter_axes({"type": "bar", "y_axis": "control_percentage"}, "control_percentage", rows) is None
    assert scatter_axes(None, "average", rows) is None


def test_rank_forms_uses_jev_probabilities(monkeypatch):
    monkeypatch.setattr(pack_charts.jev_client, "enabled", lambda: True)
    monkeypatch.setattr(pack_charts.jev_client, "ask", lambda *a, **k: {
        "form": {"choice": "stat", "probabilities": {"bars": 0.3, "stat": 0.6, "scatter": 0.1}}})
    out = rank_forms("idea", {"group_by": ["batter"]}, ["scatter", "bars", "stat"])
    assert out["by"] == "jev" and out["order"] == ["stat", "bars", "scatter"]


def test_rank_forms_falls_back_to_rules(monkeypatch):
    monkeypatch.setattr(pack_charts.jev_client, "enabled", lambda: True)
    monkeypatch.setattr(pack_charts.jev_client, "ask", lambda *a, **k: None)  # Jev failed
    out = rank_forms("idea", {}, ["line", "bars"])
    assert out == {"order": ["line", "bars"], "by": "rules", "probabilities": {}}
