"""
Credits for every note and card (Phase 0 provenance: docs/notes-pipeline.md).

FEED_CREDIT is a placeholder: the repo never names the provider of the 2015+ ball-by-ball and
line/length/shot CSVs. Fill it in (name, link, licence wording they require) and re-run
scripts/notes/build_hypothesis_notes.py; nothing else needs to change.
"""

FEED_CREDIT = "[2015+ ball-by-ball and line/length/shot feed: provider and licence to be confirmed]"
FEED_CREDIT_SHORT = "[feed provider TBC]"

PRIMER_URL = "https://twitter.com/hganjoo_153"  # the repo links only the author's X profile, not the primer

DATA_LINES = [
    "Data: Hindsight ([hindsightcricket.com](https://hindsightcricket.com)).",
    "Ball-by-ball data before 2015, and recent matches not yet in the main feed: "
    "[Cricsheet](https://cricsheet.org) (Open Data Commons Attribution License, ODC-By 1.0).",
    f"Ball-by-ball data from 2015, including line, length and shot: {FEED_CREDIT}.",
]

METRICS_LINE = (
    "Advanced metrics: Impact, RAA, WAA, WPA and leverage are computed ball by ball using "
    f"Himanish Ganjoo's T20 Primer method ([Himanish Ganjoo]({PRIMER_URL}), *T20 Metrics: A Primer*)."
)


def methodology_line(tests: str) -> str:
    return (f"Methodology: {tests}. Confidence intervals are 95% bootstrap percentile intervals "
            "(10,000 resamples of matches or innings). Definitions were registered before the "
            "analysis was run (analysis/hypotheses/preregistration).")


def credits_block(tests: str) -> str:
    lines = ["## Credits", ""] + [f"- {l}" for l in DATA_LINES] + [f"- {METRICS_LINE}", f"- {methodology_line(tests)}"]
    return "\n".join(lines)


CARD_FOOTER = "Data: Hindsight · hindsightcricket.com"
CARD_CREDITS = ("Pre-2015 & fallback ball-by-ball: Cricsheet (ODC-By) · 2015+ feed: "
                f"{FEED_CREDIT_SHORT} · Impact/RAA/WAA/WPA: Himanish Ganjoo's T20 Primer method")
