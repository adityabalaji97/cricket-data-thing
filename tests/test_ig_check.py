from services import ig_check as C


def card(title, payload, kicker=None):
    c = {"title": title, "payload": payload}
    if kicker:
        c["kicker"] = kicker
    return {"type": "card", "card": c}


def test_compare_finds_title_and_value_changes_and_ignores_storage_noise():
    old = [{"type": "hook", "text": "h"}, card("Shami 14 balls", {"rows": [[1, 2.04]]}), card("x", {"v": 1}, "The deeper cut"),
           {"type": "text", "heading": "The doubts", "body": "IPL 2026: 12 wickets"}]
    same = [{"type": "hook", "text": "h"}, card("Shami 14 balls", {"rows": [(1, 2.03)]}),
            {"type": "text", "heading": "The doubts", "body": "IPL 2026: 12 wickets"}]
    assert C.compare(old, same) == []  # tuples v lists, 2.04 v 2.03 at one decimal, the deeper cut apart: no change
    moved = [{"type": "hook", "text": "h"}, card("Shami 13 balls", {"rows": [[1, 2.0]]}),
             {"type": "text", "heading": "The doubts", "body": "IPL 2026: 13 wickets"}]
    diffs = C.compare(old, moved)
    assert diffs[0] == {"slide": 2, "was": "Shami 14 balls", "now": "Shami 13 balls"}
    assert diffs[1]["now"] == "IPL 2026: 13 wickets"
    values = [{"type": "hook", "text": "h"}, card("Shami 14 balls", {"rows": [[1, 2.4]]}),
              {"type": "text", "heading": "The doubts", "body": "IPL 2026: 12 wickets"}]
    assert C.compare(old, values)[0]["now"] == "same title, chart values changed"
