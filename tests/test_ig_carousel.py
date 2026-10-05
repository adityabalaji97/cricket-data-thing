"""Instagram carousels (services/ig_carousel.py): slides built from facts, notes and preview cards."""
from services import ig_carousel

NOTE = """*After a 10+ first over, his RAA per over moves by -0.64.*

## The claim

A common claim is that he can't recover from an expensive first over.

## How we tested it

The definitions were written down before the analysis was run ([pre-registration](https://example.com)).

## What the numbers say

**A chart caption**

```hindsight
chart: wGs1xM7de
```

## Verdict: Partly

- a. 10+ first over hurts the rest of his match: **Inconclusive**
- b. hurt by a big over from the other end: Not supported

## Caveats and sample sizes

Small samples.
"""


def test_note_sections_and_verdict():
    sections = ig_carousel.note_sections(NOTE)
    assert sections["verdict"] == "Partly"
    assert sections["the claim"].startswith("A common claim")


def test_note_carousel_is_hook_claim_verdict_end():
    slides = ig_carousel.for_note({"title": "Does one bad over break him?", "body_md": NOTE})
    assert [s["type"] for s in slides] == ["hook", "text", "verdict", "end"]
    assert slides[0]["text"] == "Does one bad over break him?"
    # One verdict part per line, markdown stripped.
    assert slides[2]["body"].split("\n") == ["a. 10+ first over hurts the rest of his match: Inconclusive",
                                             "b. hurt by a big over from the other end: Not supported"]


def test_fact_and_preview_carousels():
    fact = {"title": "X ranks 1st", "method": "Ranked by sixes among 1,593 ODI batters."}
    slides = ig_carousel.for_fact(fact, "abc123def", "Who owns the pull shot?", "ODI")
    assert [s["type"] for s in slides] == ["hook", "chart", "text", "end"]
    assert slides[1]["snapshot_id"] == "abc123def" and slides[2]["body"] == fact["method"]
    preview = ig_carousel.for_preview(["a1b2c3d4e", "f5g6h7i8j"], "2 things", "1st T20I")
    assert [s["type"] for s in preview] == ["hook", "chart", "chart", "end"]


def test_clip_keeps_whole_sentences():
    text = "First sentence here. Second sentence is longer than the rest of it. Third."
    assert ig_carousel.clip(text, 30) == "First sentence here."
    assert ig_carousel.clip("short", 30) == "short"


def test_captions_have_hook_answer_prompt_and_few_tags():
    from services import ig_captions

    cap = ig_captions.build("Who owns the pull shot in ODIs?", "Rohit Sharma ranks 1st of 1,593 ODI batters.", "debate",
                            "Ranked by sixes among 1,593 ODI batters.", ["Rohit Sharma"], "ODI")
    parts = cap.split("\n\n")
    assert parts[0] == "Who owns the pull shot in ODIs?" and parts[1].startswith("Rohit Sharma ranks 1st")
    assert "Agree, or is someone missing?" in parts
    tags = parts[-1].split("\n")[-1].split()
    assert tags[:2] == ["#RohitSharma", "#ODI"] and len(tags) <= ig_captions.MAX_TAGS
    assert ig_captions.hashtags([], "1st T20I · Lucknow", ["#INDvWI", "#TeamIndia"]) == [
        "#INDvWI", "#TeamIndia", "#T20I", "#cricket", "#cricketstats"]


def test_story_card_slides_carry_the_cards_own_json():
    card = {"id": "par", "visual": "par", "title": "Par is about 185", "payload": {"value": 185}, "sample": "T20Is"}
    slides = ig_carousel.for_story_cards([card], ["IND", "WI"], "1 thing", "1st T20I")
    assert [s["type"] for s in slides] == ["hook", "card", "end"]
    # The slide is drawn by the app's own StoryCard from this JSON (src/components/ig/IgSlide.jsx), team colours too.
    assert slides[1]["card"] is card and slides[1]["teams"] == ["IND", "WI"]
