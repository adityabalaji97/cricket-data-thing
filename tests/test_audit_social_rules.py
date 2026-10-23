import importlib.util
from pathlib import Path

from services import social_rules

_spec = importlib.util.spec_from_file_location("audit_social_rules",
                                               Path(__file__).resolve().parents[1] / "scripts" / "audit_social_rules.py")
audit_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit_mod)


def _row(i, key, source, slides, kind=None):
    return {"id": i, "angle_key": key, "source": source, "status": "ready", "planned_for": None, "kind": kind,
            "data": {"slides": slides}}


def _card(title, visual="metric_bars", **kw):
    return {"type": "card", "card": {"id": title[:5], "title": title, "visual": visual, **kw}}


def test_builder_is_the_key_family_and_source():
    assert audit_mod.builder("ig:preview-india-west-indies-2026-10-17", "ig-match-day") == "preview/ig-match-day"
    assert audit_mod.builder("ig:otd-ind-pak-mcg-2022", "hand") == "otd/hand"


def test_audit_counts_by_rule_builder_and_visual():
    rows = [_row(1, "ig:debate-a", "ig-backlog", [{"type": "hook", "text": "t"}, _card("x" * 90, "deep_compare")]),
            _row(2, "ig:debate-b", "ig-backlog", [{"type": "hook", "text": "t"}] + [_card(f"{n} runs") for n in range(9)]),
            _row(3, "ig:otd-c", "ig-otd", [{"type": "hook", "text": "t", "cover": "text-no-chart"}, _card("ok 1")])]
    got = audit_mod.audit(rows)
    rules = {r["rule"]: r for r in got["rules"]}
    assert got["packs"] == 3 and got["flagged"] == 3
    assert rules["long_title"]["by_builder"] == {"debate/ig-backlog": 1} and rules["long_title"]["by_visual"] == {"deep_compare": 1}
    assert rules["slide_count"]["packs"] == 1 and rules["bare_cover"]["by_builder"] == {"otd/ig-otd": 1}


def test_a_play_along_keeps_its_deeper_cut_where_it_is():
    slides = [{"type": "hook", "text": "t"}, _card("a 1"), _card("b 2"), _card("c 3"), _card("d 4", kicker="The deeper cut")]
    assert audit_mod.audit([_row(1, "ig:play-x", "ig-backlog", slides, kind="play")])["rules"] == []
    assert audit_mod.audit([_row(1, "ig:debate-x", "ig-backlog", slides)])["rules"][0]["rule"] == "deeper_cut_slot"


def test_every_finding_has_a_known_rule():
    slides = [{"type": "hook", "text": "t", "cover": "text-no-chart"}, _card("x" * 90, "recap_text", help="h" * 100)]
    assert {f["rule"] for f in social_rules.findings(slides)} <= set(social_rules.RULES)
