"""Phase 3: hypothesis results -> /notes markdown and share-card specs (no database needed)."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_notes", ROOT / "scripts" / "notes" / "build_hypothesis_notes.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)

RESULT = {
    "hypothesis": "H0", "slug": "h0-varun-first-over", "verdict": "Partly", "data_through": "2026-10-03",
    "headline": "After a 10+ first over ...",
    "claim": "A common claim is that Varun Chakravarthy can't recover from an expensive first over.",
    "effects": [
        {"name": "Varun: 10+ minus 0-6", "estimate": -0.6, "ci": [-1.1, -0.1], "p_value": 0.03, "test": "Welch t-test",
         "unit": "RAA per over", "direction": "negative", "meaningful": -0.5, "n": {"10+": 36, "0-6": 68},
         "detail": {"t": -2.1, "mean_10+": -0.2, "mean_0-6": 0.4}},
        {"name": "Peers", "estimate": -0.1, "ci": [-0.4, 0.2], "p_value": 0.5, "test": "Welch t-test",
         "unit": "RAA per over", "direction": "negative", "meaningful": -0.5, "n": {}, "detail": {"mean_10+": 0.1}},
    ],
    "charts": [{"key": "first_over", "caption": "Rest-of-match RAA per over", "url": "https://hindsightcricket.com/query?x=1",
                "small_samples": ["10+ (12)"], "title": "t", "params": {}, "presentation": {}}],
    "parts": {"a. first over": "Supported", "b. entry": "Inconclusive"},
    "caveats": ["A caveat."], "samples": {"matches": {"10+": 36}},
}


def test_note_has_every_required_section():
    md = build.note_markdown(RESULT)
    for heading in ("## The claim", "## How we tested it", "## What the numbers say", "## Verdict: Partly",
                    "## Caveats and sample sizes", "## Reproduce this", "## Credits"):
        assert heading in md
    assert md.startswith("*After a 10+ first over")
    assert "{{chart:first_over}}" in md
    assert "[Rest-of-match RAA per over](https://hindsightcricket.com/query?x=1)" in md
    assert "small samples (under 15) in 10+ (12)" in md
    assert "Himanish Ganjoo's T20 Primer method" in md and "Cricsheet" in md and "ODC-By" in md
    assert "pre-registration" in md and "### H0a" in md      # pre-registration embedded, headings nested
    assert md.count("Common claim:") == 0                     # its claim paragraph is not repeated


def test_cards_keep_names_and_per_part_verdict():
    cards = build.card_specs(RESULT)
    assert cards["footer"] == "Data: Hindsight · hindsightcricket.com"
    assert cards["cards"][0]["title"].startswith("Varun Chakravarthy can't")
    assert cards["cards"][1]["verdict"] == "Supported" and "a" in cards["cards"][1]["verdict_label"]
    assert all(r["label"] != "t" for r in cards["cards"][1]["rows"])
    assert 2 <= len(cards["cards"]) <= 3
