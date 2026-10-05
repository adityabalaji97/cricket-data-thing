"""Bot drafting (services/note_drafts.py): valid markdown and chart references from stub inputs."""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from services import note_drafts as nd
from services.notes import chart_ids

MATCH = {"id": "1535464", "team1": "Rajasthan Royals", "team2": "Gujarat Titans", "competition": "IPL",
         "date": "2026-05-29", "gender": "male"}
RECAP = {"available": True,
         "headline": "The middle overs decided it: Gujarat Titans batted 36 runs better than Rajasthan Royals there by Impact (+16 v -21).",
         "bullets": ["Shubman Gill's 104 off 58 added 23.5 runs to Gujarat Titans' expected total.",
                     "Gujarat Titans won by 7 wickets (Chased 215 with 8 balls to spare)."]}
RECORD = {"title": "Sai Sudharsan and Shubman Gill added 167 off 77 balls v Rajasthan Royals, joint the 6th-biggest of 3,592 IPL partnerships since 2024",
          "source": "records", "snapshot_id": "Rank12345",
          "facts": {"method": "Partnership runs ranked against 3,592 IPL partnerships since 2024.",
                    "numbers": {"runs": 167, "balls": 77}, "n": 3592, "since_year": 2024, "rank": 6}}
SERIES = {"title": "Rajasthan Royals v Gujarat Titans win probability and Impact.", "source": "recap",
          "snapshot_id": "WinProb12", "facts": {}}


def test_recap_leads_with_the_record_and_embeds_both_charts():
    draft = nd.compose_recap(MATCH, "Gujarat Titans won by 7 wickets", RECAP, [SERIES, RECORD], "WinProb12")
    assert draft["title"] == RECORD["title"]
    assert draft["dek"] == "Gujarat Titans won by 7 wickets · IPL, 29 May 2026"
    body = draft["body_md"]
    assert chart_ids(body) == ["WinProb12", "Rank12345"]
    assert "## How it was won" in body and "## The numbers that stood out" in body
    assert body.startswith(RECAP["headline"])
    # The title fact is not repeated under the headline; its method is.
    assert body.count("joint the 6th-biggest") == 0 and RECORD["facts"]["method"] in body
    assert "[Full scorecard](/scorecard/1535464)" in body


def test_recap_without_records_uses_the_recap_headline_as_title():
    draft = nd.compose_recap(MATCH, "Gujarat Titans won by 7 wickets", RECAP, [SERIES], "WinProb12")
    assert draft["title"].startswith("Rajasthan Royals v Gujarat Titans: The middle overs decided it")
    assert chart_ids(draft["body_md"]) == ["WinProb12"]
    assert not draft["body_md"].startswith("The middle overs")  # already the title


def test_basic_data_match_with_records_but_no_primer():
    draft = nd.compose_recap(MATCH, "Gujarat Titans won by 7 wickets", None, [RECORD], None)
    assert draft["body_md"].startswith("Gujarat Titans won by 7 wickets.")
    assert chart_ids(draft["body_md"]) == ["Rank12345"]


def test_nothing_to_say_is_no_draft():
    assert nd.compose_recap(MATCH, "Gujarat Titans won by 7 wickets", None, [SERIES], None) is None
    assert nd.compose_recap(MATCH, "x", {"available": False}, [], None) is None


FIXTURE = {"team1": "India", "team2": "West Indies", "venue": "Maharaja Yadavindra Singh International Cricket Stadium, Mullanpur",
           "format": "ODI", "start_utc": "2026-10-03T08:30:00+00:00", "match_id": "1529229",
           "series": "WEST INDIES TOUR OF INDIA", "event_type": "ODI", "is_live": False}
SECTIONS = [{"id": "venue_profile", "title": "Venue Profile", "bullets": ["Chasing sides have won 4 of 6 here."]},
            {"id": "head_to_head", "title": "Head-to-Head", "bullets": ["India lead West Indies 7-3 in their last 10 meetings."]}]


def test_preview_places_the_venue_chart_and_links_the_full_preview():
    known = [{"facts": ["India lead West Indies 7-3 in their last 10 meetings."]}]
    draft = nd.compose_preview(FIXTURE, SECTIONS, "India lead West Indies 7-3 in their last 10 meetings.", known,
                               {"id": "Venue1234", "lead": "The leading batters at Mullanpur since 2019, by runs:"})
    assert draft["title"] == "India v West Indies preview: India lead West Indies 7-3 in their last 10 meetings"
    assert "Sat 3 Oct, 14:00 IST (08:30 GMT)" in draft["dek"]
    body = draft["body_md"]
    assert body.index("## Venue Profile") < body.index("chart: Venue1234") < body.index("## Head-to-Head")
    assert "fmt=mens-odi" in body and "autoload=true" in body


def test_preview_title_falls_back_without_a_ranked_headline():
    draft = nd.compose_preview(FIXTURE, SECTIONS, None, [], None)
    assert draft["title"] == "India v West Indies at Maharaja Yadavindra Singh International Cricket Stadium: match preview"
    assert chart_ids(draft["body_md"]) == []


def test_fixture_scope_tells_leagues_from_internationals():
    from services.content_rules import in_scope

    assert in_scope(nd.fixture_scope(FIXTURE))
    ipl = {**FIXTURE, "team1": "Mumbai Indians", "team2": "Chennai Super Kings", "format": "T20",
           "series": "Indian Premier League", "event_type": "T20"}
    assert nd.fixture_scope(ipl)["match_type"] == "league" and in_scope(nd.fixture_scope(ipl))
    minor = {**FIXTURE, "team1": "Namibia", "team2": "United Arab Emirates"}
    assert not in_scope(nd.fixture_scope(minor))


def test_preview_candidates_keep_only_the_next_36_hours():
    db = MagicMock()
    db.execute.return_value.first.return_value = None   # no preview note yet
    now = datetime(2026, 10, 2, 0, 0, tzinfo=timezone.utc)
    soon = {**FIXTURE, "start_utc": (now + timedelta(hours=10)).isoformat()}
    later = {**FIXTURE, "match_id": "2", "start_utc": (now + timedelta(hours=40)).isoformat()}
    started = {**FIXTURE, "match_id": "3", "start_utc": (now - timedelta(hours=1)).isoformat()}
    live = {**soon, "match_id": "4", "is_live": True}
    assert [f["match_id"] for f in nd.preview_candidates(db, [soon, later, started, live], now=now)] == ["1529229"]



STORY = {"fixture": {"params": {"venue": "Wankhede Stadium, Mumbai"}}, "chapters": [
    {"id": "glance", "title": "At a glance", "cards": [
        {"id": "glance", "title": "Par about 212, no clear edge for chasing", "sample": "MI v CSK"},
        {"id": "par", "title": "Par here is about 212", "sample": "IPL 2026 at Wankhede Stadium · T20 Primer par"}]},
    {"id": "ground", "title": "The ground", "cards": [
        {"id": c, "title": f"Card {c}", "sample": "s"} for c in ("results", "totals", "phases", "pace-spin", "extra")]},
]}


def test_preview_note_is_built_from_the_story_cards():
    built = nd.story_sections(STORY)
    assert built["headline"] == "Par about 212, no clear edge for chasing"
    glance, ground = built["sections"]
    assert glance["bullets"] == ["Par here is about 212 (IPL 2026 at Wankhede Stadium · T20 Primer par)."]
    assert ground["cards"] == ["results", "totals", "phases", "pace-spin"]  # the featured four, not "extra"
    draft = nd.compose_preview(FIXTURE, built["sections"], built["headline"], [{"facts": built["facts"]}],
                               {"id": "Card12345", "lead": "The ground's standout card:"})
    body = draft["body_md"]
    assert body.index("## The ground") < body.index("chart: Card12345")
    assert "story=1" in body
