from datetime import date, datetime, timezone

from services import preview_news as N

GOOGLE_ITEM = b"""<?xml version="1.0"?><rss><channel>
<item><title>Santner injury worry compounds Black Caps woes - NZ Herald</title><link>https://news.google.com/a</link>
<pubDate>Thu, 22 Oct 2026 14:19:00 GMT</pubDate><description>&lt;a href="x"&gt;Santner injury worry compounds Black Caps woes&lt;/a&gt;</description>
<source url="https://www.nzherald.co.nz">NZ Herald</source></item>
<item><title>No date here - Somewhere</title><link>https://news.google.com/b</link></item>
</channel></rss>"""


def test_google_item_outlet_split_from_title_and_date_kept():
    items = N.parse(GOOGLE_ITEM, "Google News", "q")
    a = items[0]
    assert (a["title"], a["outlet"]) == ("Santner injury worry compounds Black Caps woes", "NZ Herald")
    assert a["published_at"] == datetime(2026, 10, 22, 14, 19, tzinfo=timezone.utc)
    assert a["summary"] is None  # Google's description only repeats the headline


def test_scope_big_sides_and_leagues_not_league_two():
    assert N.is_big({"team1": "New Zealand", "team2": "India", "series": ""})
    assert N.is_big({"team1": "Mumbai Indians", "team2": "Chennai Super Kings", "series": "Indian Premier League"})
    assert not N.is_big({"team1": "United Arab Emirates", "team2": "Netherlands", "series": "ICC Men's Cricket World Cup League 2"})


def test_general_feeds_need_both_sides_by_any_name():
    assert N.names_both("Black Caps v India, first T20", "New Zealand", "India")
    assert not N.names_both("India register their highest chase", "New Zealand", "India")


def test_dedupe_by_link_and_near_identical_title():
    t = datetime(2026, 10, 22, tzinfo=timezone.utc)
    items = [{"title": "Samson stars as India chase 206", "url": "u1", "published_at": t},
             {"title": "Samson stars as India chase 206!", "url": "u2", "published_at": t},
             {"title": "Samson stars as India chase 206", "url": "u1", "published_at": t},
             {"title": "Santner injury worry", "url": "u3", "published_at": t}]
    assert [i["url"] for i in N.dedupe(items)] == ["u1", "u3"]


def test_fixture_key():
    assert N.fixture_key({"date": date(2026, 10, 24), "team1": "New Zealand", "team2": "India"}) == "2026-10-24|New Zealand|India"
