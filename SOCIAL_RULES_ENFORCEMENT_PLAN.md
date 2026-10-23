# Social rules enforcement: plan

Status: **draft** (23 Oct 2026), waiting on the decisions at the end. Owner: Claude Code / Codex, one chunk per session.

## The problem

The rules for posts live in `docs/social_rules.md`, but code enforces only part of them, and nothing stops a post that
breaks one. So the user spots the same problems by hand on every post (23 Oct: a text-only cover, a text "How it was
won" slide, "1 overs", a scorecard title with no claim).

How the rules are checked today:

- `services/social_rules.lint_slides` runs in `ig_backlog.upsert_pack` on every queued post. Its findings are saved in
  `content_packs.rule_warnings` and shown in the admin as amber lines. **It never stops a post.**
- It tests title length (80 characters), lists of more than three, house vocabulary, long help lines, the one-row
  ring, more than 8 slides, the cover chart repeating in the deck, and the deeper cut's slide. PR #198 (23 Oct) added
  a cover with no chart, a text card, and a count of one with a plural noun ("1 overs").
- It can't see layout. Whether a title wraps to 3 lines, a footer wraps, a legend is drawn or a label is cut off
  only shows up once the slide is rendered.

What it finds today, across the 77 ready Instagram posts (23 Oct):

| Warning | Count | Where it comes from |
|---|---|---|
| Title over 80 characters | 51 | the deeper-cut card (`services/ig_posts/deep_cut.py`, `deep_compare`): 27; previews 10; spotlights 11; trend 6 |
| Long help line | 32 | debates 14, article spotlights 7, the rest spread out |
| Off-vocabulary word | 28 | debates 10, on this day 5, trend 3, storylines 3 |
| More than 8 slides | 22 | debates (`ig_backlog`) 11, match-day previews (`scripts/ig_match_day.py`) 9 |
| No chart on the cover | 6 | match-day previews 3, recap 1, debate 1, IPL 1 |
| Deeper cut not on slide 3 | 4 | play-alongs (check whether the play exemption is being passed) |
| Text card, "1 runs", repeated cover chart | 1-2 each | otd (fixed in PR #198), a debate, an article spotlight |

The builders were written before most of these rules (cover A/B 19 Oct, card anatomy 22 Oct) and were never updated
to follow them. Warnings pile up, and nobody acts on them.

## The idea

Three layers, in this order:

1. **See everything.** Lint what the data can show, and measure what only the drawn slide can show.
2. **Fix the builders** that produce most of the warnings, so the same post can't break the same rule twice.
3. **Then gate:** the serious rules keep an automatic post out of the day's plan until it's fixed. This only works
   once layer 2 has removed most violations; before that it would bench most of the queue.

## Chunks

### Chunk 0: audit script (baseline)

- `scripts/audit_social_rules.py`: lint every ready (and optionally recently posted) Instagram pack. Print counts by
  rule × builder (`source` + key prefix + card visual), with one example each. `--json` gives the same for the digest.
- Record today's baseline in this file (the table above) so every later chunk shows its effect.
- Done when: the script reproduces the table above on production.

### Chunk 1: layout checks at render time

- `IgSlide` / `StoryCard`: put data attributes on the measured parts: `data-card-title`, `data-card-footer`,
  `data-legend` (every Legend/Chip legend) and `data-story-chart` (already there).
- `scripts/render_ig_slides.mjs`: after `data-ready`, measure each slide and add `layout: [...]` to its result:
  - title over 2 lines (height ÷ line height)
  - footer over 1 line
  - any `data-legend` present
  - text cut off: an element whose `scrollWidth` or `scrollHeight` exceeds its box, or an SVG `<text>` whose
    bounding box falls outside its SVG
  - the chart area under a minimum share of the card
- `services/ig_slides.render`: merge the layout findings into the pack's `rule_warnings` as "Slide n: …".
- Tests: a fixture page with a 3-line title and a clipped label. The renderer reports both.
- Done when: re-rendering today's queue shows layout warnings next to the lint warnings in the admin.

### Chunk 2: deeper-cut titles (27 of the 51 long titles)

- `services/ig_posts/deep_cut.py`: the card title becomes a short claim (≤ 80 characters) with the player and the
  number first, in house vocabulary ("Starc: 2.1 runs an over below par in the powerplay"). The full sentence stays
  as the caption line (`ig_captions.with_deep_cut`).
- A unit test over every deep-cut template, using the longest names in `player_identity`: every title ≤ 80.
- Rebuild the queued posts that carry a deeper cut (`ig_backlog.refresh`).

### Chunk 3: deck length and help lines

- Debates (`ig_backlog`) and match-day previews (`scripts/ig_match_day.py`, `services/ig_posts/match.py`): cap at
  8 slides. Each builder declares its drop order (the lowest-appeal cards go first; the cover, the lead and the
  deeper cut always stay).
- Help lines: check whether an over-long help line is actually drawn on the card face. If it is, move it to the info
  sheet or caption. If it isn't, the lint rule is wrong and should change.
- Vocabulary slips at the source: fix every builder that the chunk-0 audit shows writing "runs added", "balls per
  dismissal" and the like.

### Chunk 4: covers and the rest

- Match-day previews, recaps, debates and IPL posts with no chart on the cover: make each one's lead card a chart that
  can go on the cover (`ig_cover.hero_from`), as on-this-day now does.
- Play-alongs: confirm the deeper-cut position exemption reaches the lint (`fact.kind == "play"`).
- Done when: the chunk-0 audit shows no warning type above 5 across the queue.

### Chunk 5: the gate

- `services/social_rules.py`: label each rule **hard** or **soft** (see Decisions). `lint_slides` returns the label
  with each finding.
- `ig_backlog.upsert_pack`: an automatic post (any source but `hand` / `article`) with a hard finding goes to the bench
  instead of the day's plan, with its reasons saved. The admin shows benched posts with the reason and a "fix and
  re-queue" link (the builder's `--force` rebuild).
- Morning digest (`ig_plan.digest`): "benched by the rules: N", with each reason.
- Behind `SOCIAL_RULES_GATE=on`, switched on only after chunk 4's audit is clean.

### Chunk 6: keep it from coming back

- The nightly workflow runs `audit_social_rules.py` after the post builders. It prints the table into the run summary
  and fails a non-blocking step if any hard rule appears.
- `docs/social_rules.md`: each rule marked "checked by code (lint / layout / gate)" or "by eye", so the gap stays
  visible.
- Any new rule the user sets gets a lint or layout check in the same change, or is explicitly marked "by eye".

## Decisions (the user's)

1. **Hard rules (they bench a post).** Recommended: no chart on the cover; a text-only card; a title over 2 lines
   (rendered); more than 8 slides; text cut off. Everything else stays a warning.
2. **Hand-made posts.** Recommended: warn but never bench them (the user is already looking at them).
3. **The cover A/B.** Leave the text side as a valid cover until the test ends (~2 Nov), then decide from the
   Instagram numbers. "No chart possible" is already a hard finding regardless.

## Status

| Chunk | Status |
|---|---|
| 0 Audit script | [ ] |
| 1 Layout checks at render | [ ] |
| 2 Deeper-cut titles | [ ] |
| 3 Deck length, help lines, vocabulary | [ ] |
| 4 Covers and the rest | [ ] |
| 5 The gate | [ ] |
| 6 Keep it from coming back | [ ] |
