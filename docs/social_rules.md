# Social rules

Working rules for Hindsight's social posts, Reels and X replies, learned from the owner's corrections and Instagram's
numbers (Oct 2026); the Reddit study's title rules are docs/content_guidelines.md. One source for people and code: `services/social_rules.py` reads the sections below into the
Reel writer's and checker's prompts and into Jev's appeal scoring, and checks every queued post's slides against the
rules code can test (warnings in the admin's Daily posts tab). Edit a rule here and the prompts follow.

## Card anatomy

Every card, on the site and in every image, is three things: the claim, the picture, and enough context to trust it. A
reader gives it about three seconds. Anything that doesn't change how a cricket fan reads the chart leaves the card for
the caption, the thread or the card's info sheet.

- **Title:** one claim, at most two lines (about 80 characters): who, what, one number. The axes already name lines,
  lengths and phases, so the title doesn't repeat them.
- **No help line on the card face.** Definitions, thresholds and method go in the info sheet (site) and the caption
  (posts). A card may keep one help line only when the chart can't be read without it (`help_on_card`).
- **Inside the chart:** one number per mark. A second number (balls, wickets) only when the claim depends on it.
  Legends are colour chips, not sentences; no "how to read" notes.
- **Footer:** the scope on one line (who, against what, when), then the credit line:
  "hindsightcricket.com · Data: Himanish Ganjoo & TechRadar, Cricsheet". Always full names.
- **Slide counter** ("2 / 7") only in carousels, where swiping matters; never on reply images or single cards.
- **Caveats** (hand-tagged data coverage, small samples beyond the "small sample" chip) go in the caption.

## Vocabulary

One term per idea, the same everywhere: cards, captions, threads, Reels.

| Idea | Say |
|---|---|
| Impact | Impact |
| RAA | runs above par |
| WPA | win probability added |
| Control | control % or false shots |
| Balls per dismissal | balls per wicket |
| Strike rate | SR, or "scores at 106" |
| Lengths | full, good length, back of a length, short, yorker, full toss |
| Lines | wide outside off, outside off, on the stumps, down leg, wide down leg |
| Phases | powerplay, middle overs, death (not "new ball" / "old ball") |

## Numbers

- Every number on a slide comes from the query builder; code writes titles from the numbers. Figures from elsewhere are credited text, never charted, and only used once confirmed.
- T20 posts lead with Impact and win probability added (WPA); strike rate and average are context. ODIs have no Impact.
- Say what a stat means and whether it reflects skill before using it (luck-driven stats, like "conversion", are out).
- A claim must be exactly true for its whole scope: "every year" only if every year in the table holds; "among India's pacers" never becomes "no one".
- A team total never stands in for one player: split it to show whose numbers moved.
- Test a viral claim's premise before arguing it.
- Compare like with like (spinners with spinners), set minimum samples for rates, and flag small samples.
- Don't blame players, bowlers especially: separate execution, batting skill and conditions. Give balanced verdicts: the case both ways.

## Carousels

- A "case for a player" post tells a story: career, turning point, the rival's rise, his old role now, the rest of the case, both ways.
- "The deeper cut" is slide 3.
- At most 8 slides: Instagram counts how many viewers reach the last one. Fold a slide that only repeats earlier titles into the caption.
- The cover (slide 1) carries a reason to stop: the hook, and on the hero side of the cover test (services/ig_cover.py) the lead chart's top rows.
- A chart on the cover never appears again in the deck: the cover takes the lead chart's top rows and the chart leaves the deck, so slide 2 is new (it's the one Instagram re-shows to people who scrolled past). The full chart goes on the X thread's first tweet. This holds for hand-built posts too (ig_cover.without_hero_card; the slide check flags a repeat).
- Bold cards, a one-line header and footer, no legend; the data credit in the footer; no player photos or logos.
- A card title fits the slide: 110 characters at most.
- No list of more than three items in one sentence.
- A "best" ring marks a column only where the values compare: none where only one row has a value. One measure, one shading scale.
- Date windows run to today, so a rebuild takes the latest game.

## Reels

- Short, about 25-30 seconds, by default. Long Reels averaged half the views (508 v 1,041) and held 27% of viewers past 3 seconds against 46%.
- Instagram shows a Reel to about 200 non-followers first and widens it only if they keep watching past 3 seconds: the hook decides the Reel.
- The hook names one player and gives one plain number. A question hook needs a number.
- No metric names in the hook (Impact, WPA, win probability, runs above average, "per 100"): explain an advanced metric inline, later, the first time it is used. Say WPA as percentage points.
- Preview and recap Reels open on a player, not a ground statistic or a scoreline people saw last night.
- A trend on X doesn't carry to Instagram: open with the fans' argument in plain words, then the number.
- End on the strongest argument, not a non-finding. A closing question only after that point is made.

## X

- A reply to a viral take is one tweet under 280 characters with four image cards.
- A thread's first tweet carries the lead chart (slide 2) with the hook and its claim, not a text-only cover: X gives native images more reach, and the first 30 minutes decide most of it. Links only in the last tweet.
- In a thread, a player's first mention is a hashtag; each tweet ends with the lead tag and #CricketTwitter; credit @himganj153 and @TechRadar9; the last tweet links the post's page.

## Appeal

- What draws strangers on Instagram (77-83% of views come from non-followers through the Reels tab): one named player with one striking number, such as a record, a home-ground figure, or two innings compared.
- What doesn't: ground statistics, a result already seen the night before, or a debate that is trending on X but needs our own metric to explain.
