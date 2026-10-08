from datetime import date

from services import ig_season as S


def test_focus_follows_india_then_a_major_series():
    assert S.focus(date(2026, 10, 9)) == ("T20", "India v West Indies T20Is")
    assert S.focus(date(2026, 10, 19)) == ("T20", "India in New Zealand T20Is")  # 3 days before the first T20I
    assert S.focus(date(2026, 11, 2)) == ("ODI", "India in New Zealand ODIs")
    assert S.focus(date(2026, 10, 18)) is None
    assert S.focus(date(2026, 10, 18), [("ODI", "Australia v England ODIs")]) == ("ODI", "Australia v England ODIs")


def test_post_format_from_key_then_words():
    assert S.post_format({}, "ig:debate-odiwc-batter-all") == "ODI"
    assert S.post_format({}, "ig:odi-fastest-5000") == "ODI"
    assert S.post_format({}, "ig:ipl-fastest-1000-balls") == "T20"
    assert S.post_format({"title": "Is Virat Kohli the most complete batter in ODIs since the 2023 World Cup?"}) == "ODI"
    assert S.post_format({"kicker": "IPL", "title": "x"}) == "T20"
    assert S.post_format({"title": "Does one bad over break Varun Chakravarthy?"}) is None
