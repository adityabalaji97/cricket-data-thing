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
    thread = x_thread(s, CAPTION, {"abc": "Bumrah saves the most at the death"})
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
         {"type": "card", "card": {"visual": "win_prob_line", "title": "India never had better than 30%",
                                   "payload": {"bands": [{"over": 5, "text": "Paul removed Samson", "from": 30, "to": 16}]}}}]
    thread = x_thread(s, CAPTION)
    assert thread[0]["text"].startswith("247 was 59 above par. Hope added 39.9. Paul saved 19.2.")
    assert "Over 5: Paul removed Samson (30→16%)" in thread[1]["text"]
