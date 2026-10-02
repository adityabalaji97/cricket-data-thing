"""Which chart an idea pack should use: ranked bars, a trend line, a scatter, or one big number.

Code decides which forms the data can support (a line needs a time grouping, a scatter needs two
metrics over enough rows, a stat card needs a subject). Jev, when configured, ranks the valid
forms for the idea; without it a fixed rule order decides. Every valid form is rendered as its own
snapshot so the admin page can switch between them (api/img.mjs draws each layout).

Rule from the feature plan: the charted metric is the ranking metric; threshold filters ("50+
average") only narrow the rows, they are not a second axis. A scatter is offered only when the
question itself names two metrics (nl2query's recommended_chart is a scatter with both axes).
"""
from typing import Any, Dict, List, Optional

from services import jev_client

TIME_KEYS = ("year",)
MIN_LINE_POINTS = 3
MIN_SCATTER_ROWS = 8

FORMS = {
    "bars": "A ranked bar list: who leads on one stat, with the subject highlighted at its rank.",
    "line": "A trend line over seasons: how one stat changed over time.",
    "scatter": "A scatter of two stats across many players or teams, the subject highlighted: how two qualities combine.",
    "stat": "One big headline number with its rank: the single striking fact, little else.",
}


def valid_forms(shape: Dict[str, Any]) -> List[str]:
    """Forms the data supports, in the rule-based preference order.

    shape: {group_by, rows, has_subject, scatter: (x_metric, y_metric) | None}
    """
    group_by = shape.get("group_by") or []
    n = int(shape.get("rows") or 0)
    time_key = next((g for g in group_by if g in TIME_KEYS), None)
    out: List[str] = []
    # A trend is the point when the idea is grouped by season with a single series.
    if time_key and len(group_by) == 1 and n >= MIN_LINE_POINTS:
        out.append("line")
    if shape.get("scatter") and n >= MIN_SCATTER_ROWS and not time_key:
        out.append("scatter")
    if n >= 2:
        out.append("bars")
    if shape.get("has_subject"):
        out.append("stat")
    return out


def rank_forms(idea: str, shape: Dict[str, Any], forms: List[str]) -> Dict[str, Any]:
    """Order the valid forms for this idea. Returns {order: [...], by: 'jev'|'rules', probabilities}."""
    if len(forms) <= 1 or not jev_client.enabled():
        return {"order": forms, "by": "rules", "probabilities": {}}
    answers = jev_client.ask(
        {
            "idea": idea,
            "grouped_by": shape.get("group_by"),
            "ranked_by": shape.get("metric"),
            "rows": shape.get("rows"),
            "subject": shape.get("subject"),
            "audience": "cricket fans scrolling a phone feed (Reddit, X); one message per image",
        },
        {
            "form": {
                "type": "choice",
                "instructions": "Which chart form communicates this cricket stat idea best in a single phone-sized image?",
                "criteria": {f: FORMS[f] for f in forms},
            }
        },
        timeout=3.0,
    ) or {}
    probs = ((answers.get("form") or {}).get("probabilities")) or {}
    probs = {f: float(p) for f, p in probs.items() if f in forms}
    if not probs:
        return {"order": forms, "by": "rules", "probabilities": {}}
    order = sorted(forms, key=lambda f: (-probs.get(f, 0.0), forms.index(f)))
    return {"order": order, "by": "jev", "probabilities": {f: round(p, 3) for f, p in probs.items()}}


def scatter_axes(parsed_chart: Optional[Dict[str, Any]], metric: str, rows: List[Dict[str, Any]]) -> Optional[tuple]:
    """(x, y) when the parsed question asked for two metrics and both are in the rows."""
    chart = parsed_chart or {}
    if str(chart.get("type") or "").lower() != "scatter":
        return None
    x, y = chart.get("x_axis"), chart.get("y_axis") or metric
    if not x or not y or x == y or not rows or x not in rows[0] or y not in rows[0]:
        return None
    return (x, y)
