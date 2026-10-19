from services.ig_x import LIMIT, LINK, players_in, tag_players, tags_from_caption, weight, x_thread

CAPTION = "India v West Indies · 1st T20I\n\n• Par about 185\n\nFree ball-by-ball cricket stats: link in bio.\n.\n#INDvWI #TeamIndia #T20I #cricket"


def slides(n_cards=3, title="Par about 185, no clear edge for chasing"):
    return ([{"type": "hook", "text": "6 things the data says before India v West Indies", "kicker": "1st T20I · Lucknow"}]
            + [{"type": "card", "card": {"id": f"c{i}", "title": title}} for i in range(n_cards)]
            + [{"type": "verdict", "verdict": "Partly", "body": "Holds at the death\nnot in the powerplay"},
               {"type": "chart", "snapshot_id": "abc"},
               {"type": "end", "heading": "The full preview", "body": "Every card, free on Hindsight."}])


def test_one_tweet_per_slide_with_tags_and_numbering():
    s = slides()
    thread = x_thread(s, CAPTION, {"abc": "Bumrah saves the most at the death"}, lead_chart=False)
    assert [t["slide"] for t in thread] == list(range(1, len(s) + 1))
    assert thread[0]["text"].startswith("1st T20I · Lucknow: 6 things the data says")
    assert "🧵" in thread[0]["text"] and f"1/{len(s)}" in thread[0]["text"]
    assert thread[1]["text"].startswith("Par about 185")
    assert thread[4]["text"].startswith("Verdict: Partly. Holds at the death not in the powerplay")
    assert thread[5]["text"].startswith("Bumrah saves the most")  # a chart slide takes its chart's title
    assert LINK in thread[-1]["text"] and all(LINK not in t["text"] for t in thread[:-1])
    assert all("#INDvWI #CricketTwitter" in t["text"] for t in thread)


def test_every_tweet_fits_and_long_text_is_cut_at_a_word():
    thread = x_thread(slides(title="word " * 120), CAPTION)
    assert all(weight(t["text"]) <= LIMIT for t in thread)
    assert "…" in thread[1]["text"] and "#INDvWI" in thread[1]["text"]  # the body is cut, never the tags


def test_tags_default_when_the_caption_has_none():
    assert tags_from_caption("no tags here") == ["#cricket"]
    assert tags_from_caption("") == ["#cricket"]


def test_first_mention_of_each_player_is_a_hashtag():
    texts = ["Shai Hope made 102. Hope again", "Paul removed Samson & Kishan", "Hope and Paul, the hope of WI"]
    names = ["Shai Hope", "Keemo Paul", "Sanju Samson", "Ishan Kishan"]
    assert tag_players(texts, names) == ["#ShaiHope made 102. Hope again", "#KeemoPaul removed #SanjuSamson & #IshanKishan",
                                         "Hope and Paul, the hope of WI"]


def test_a_shared_surname_is_not_tagged_alone():
    out = tag_players(["Yadav bowled; Prince Yadav then Mayank"], ["Prince Yadav", "Mayank Yadav"])
    assert out == ["Yadav bowled; #PrinceYadav then #MayankYadav"]


def test_players_come_from_the_cards_not_the_teams():
    s = [{"type": "card", "teams": ["India", "West Indies"], "card": {"payload": {
        "rows": [{"name": "Shai Hope", "team": "West Indies"}, {"label": "Good length (SR 128)"}],
        "legend": ["India", "West Indies"], "batting": [{"name": "Sanju Samson"}]}}}]
    assert players_in(s) == ["Shai Hope", "Sanju Samson"]


def test_text_visuals_tweet_their_words():
    s = [{"type": "card", "card": {"visual": "recap_text", "title": "How it was won",
                                   "payload": {"headline": "247 was 59 above par.", "bullets": ["Hope added 39.9.", "Paul saved 19.2.", "Won by 24."]}}},
         {"type": "card", "card": {"visual": "win_prob_line", "title": "India never had better than 30",
                                   "payload": {"bands": [{"over": 5, "text": "Paul removed Samson", "from": 30, "to": 16}]}}}]
    thread = x_thread(s, CAPTION)
    assert thread[0]["text"].startswith("247 was 59 above par.\nHope added 39.9.\nPaul saved 19.2.\nWon by 24.")
    assert thread[1]["text"].startswith("India never had better than 30.\nOver 5: Paul removed Samson (30→16%)")


def test_the_last_tweet_links_to_the_posts_own_page():
    from services.ig_links import post_link, query_path

    assert post_link({"kind": "recap", "match_id": "1529233"}) == \
        "hindsightcricket.com/scorecard/1529233?utm_source=x&utm_medium=thread"
    q = query_path({"leagues": ["IPL"], "start_date": "2023-01-01", "min_balls": 120}, ["bowler"])
    assert q == "/query?leagues=IPL&start_date=2023-01-01&min_balls=120&group_by=bowler&fmt=mens-t20"
    assert post_link({"kind": "debate", "link": q}).endswith(q + "&utm_source=x&utm_medium=thread")
    assert post_link({"kind": "record", "note_slug": "fastest-to-2000"}).startswith("hindsightcricket.com/notes/fastest-to-2000?")
    assert post_link({}) == "hindsightcricket.com/links?utm_source=x&utm_medium=thread"
    long_link = post_link({"kind": "debate", "link": q + "&x=" + "y" * 200})
    thread = x_thread(slides(), CAPTION, link=long_link)
    assert long_link in thread[-1]["text"] and weight(thread[-1]["text"]) <= LIMIT  # a link counts as 23 however long


def test_a_team_subject_is_not_a_player_page():
    from services.ig_links import post_link

    assert "/player" not in post_link({"kind": "idea", "subject": "Gujarat Titans"})
    assert "/player" not in post_link({"kind": "idea", "subject": "West Indies"})


def test_a_surname_with_a_particle_is_a_name():
    out = tag_players(["Quinton de Kock's 78*", "de Kock & Rohit hit 16"], ["Quinton de Kock", "Rohit Sharma"])
    assert out == ["#QuintondeKock's 78*", "de Kock & #RohitSharma hit 16"]
    assert players_in([{"type": "card", "card": {"payload": {"rows": [{"name": "Quinton de Kock"}]}}}]) == ["Quinton de Kock"]


def test_a_tweet_carries_the_numbers_the_slide_draws():
    from services.ig_x import details

    bars = {"visual": "metric_bars", "title": "Gayle's +28.8 is in the top 2%",
            "payload": {"metric": {"format": "signed1"}, "rows": [
                {"name": "Shikhar Dhawan", "value": 67.9, "detail": "2023 · PBKS v SRH"},
                {"name": "Priyansh Arya", "value": 66.8}, {"name": "KL Rahul", "value": 61.7},
                {"name": "Abhishek Sharma", "value": 61.2}, {"name": "Chris Gayle", "value": 28.8, "highlight": True}]}}
    assert details(bars) == ["Shikhar Dhawan +67.9 (2023 · PBKS v SRH)", "Priyansh Arya +66.8", "KL Rahul +61.7",
                             "→ Chris Gayle +28.8"]
    comp = {"visual": "deep_compare", "title": "x", "payload": {"metric": {"format": "pct0"},
            "series": ["This match", "Since 2023"], "rows": [{"label": "Good length", "subject": 22, "field": 40}]}}
    assert details(comp) == ["Good length: 22% this match v 40% since 2023"]


def test_stat_lines_are_dropped_whole_to_fit():
    s = [{"type": "card", "card": {"visual": "recap_text", "title": "How", "payload": {
        "headline": "Head.", "bullets": ["line " * 30, "short one"]}}}]
    text = x_thread(s, CAPTION)[0]["text"]
    assert weight(text) <= LIMIT and "…" not in text.split("\n\n")[0]


def test_the_first_tweet_carries_the_lead_chart_and_the_hook():
    s = slides()
    thread = x_thread(s, CAPTION, {"abc": "Bumrah saves the most at the death"})
    assert len(thread) == len(s) - 1  # the hook no longer has a tweet of its own
    assert thread[0]["slide"] == 2  # the lead card's chart is the image
    assert thread[0]["text"].startswith("6 things the data says before India v West Indies\n\nPar about 185")
    assert "🧵" in thread[0]["text"] and f"1/{len(s) - 1}" in thread[0]["text"]
    assert [t["slide"] for t in thread[1:]] == list(range(3, len(s) + 1))
    assert all(weight(t["text"]) <= LIMIT for t in thread)
