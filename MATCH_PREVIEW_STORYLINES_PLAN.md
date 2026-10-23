# Match preview storylines: plan

Status: **signed off** (21 Oct 2026). Owner: Claude Code / Codex, one chunk per session.

## The problem

1. **The home page hides tomorrow's big match.** `TodaySection` (src/components/LandingPage.jsx) shows only today's
   fixtures whenever there are any, and falls back to upcoming ones only on a day with no cricket. On 21 Oct the API
   returned New Zealand v India for 22 Oct, but Afghanistan v Bangladesh (ODI) today hid it. It also asks for just 8
   fixtures worldwide, so a busy day of minor internationals can push a big match out entirely.
2. **Previews read as generic.** Every preview runs the same seven chapters in the same order (spec.CHAPTERS), ranked by
   sample size and distinctiveness. Nothing in it knows what people are arguing about this week: who's been dropped,
   what the captain said, the pitch talk, the milestone. The stats are right; the story is missing.

## The idea

Read what's being said about the match, turn each talking point into a question, answer it from the database, and lead
the preview with those answers. **Headlines pick the questions; every number still comes from the data** (the rule the
trend radar already follows, services/ig_posts/trends.py). Where the talk and the data disagree, that's the best card
of all ("Everyone says X. The data says Y").

What exists already and gets reused:

| Piece | Where |
|---|---|
| Headline feeds (Reddit r/Cricket, r/IndiaCricket, Cricinfo RSS, Google News RSS), player-name matching | services/ig_posts/trends.py |
| Jev appeal scoring (how much fans would argue about something) | services/ig_posts (Jev) |
| Story preview: card registry, chapters, relevance ordering, info sheets | services/preview_cards/ (spec.py, copy.py) |
| Nightly preview warm-up | scripts/warm_previews.py |
| Copy guards: numbers on a slide must come from the facts | services/content_rules.py, docs/social_rules.md |
| Query builder for every test | services/query_builder_v2.py |

## Rules (from what's worked and what hasn't)

- A talking point is only shown with a data answer. No answer, no card: it may still feed the intro as context.
- Test the premise before arguing it (social_rules: the "WI middle-order struggle" wasn't in the data).
- No blame on bowlers ([[no-blame-framing]]); a selection or form story is told both ways.
- Sources are credited and linked: headline + outlet + time. **Never reproduce article text**; at most a few words of a
  quote, attributed, with the link. Unconfirmed team news is labelled "reported".
- Thin samples are flagged as on every other card.

## Chunks

### Chunk 0: home page shows the next big match (small, independent)
- `TodaySection`: show today's matches **plus anything starting in the next 36 hours**, with "Tomorrow" on the badge,
  live first, then by start time. Ask the API for 20 fixtures, not 8.
- Rank so a big match never drops off: live > today > tomorrow; within a day, India / top-10 sides / major leagues
  first (services/competition_aliases.py already knows the leagues).
- Test: a fixture list with one minor match today and NZ v India tomorrow shows both.

### Chunk 1: news per fixture
- `services/preview_news.py`: for each fixture in the next 3 days, Google News RSS searches built from the teams and
  series ("India New Zealand T20", "India squad", "{captain} press conference"), plus the existing Reddit/Cricinfo feeds
  filtered to the two teams. Keep title, outlet, url, published time, and the feed's own one-line summary.
- Store in a new table `fixture_news` (migration in scripts/migrations/), de-duplicated by url and near-identical title.
- Runs in the nightly workflow and again on match morning (T-6h), so the toss-day talk is in.

### Chunk 2: talking points
- One model call per fixture turns that day's headlines into a short list of talking points, as structured output:
  `{claim, kind, players, team, sources[]}` where kind is selection, form, matchup, conditions, milestone, record,
  injury or tactics. Players resolved with the trend radar's matcher (full names; surnames only when unique).
- Jev scores each point for appeal; keep the top 5.
- Stored on the fixture (`fixture_storylines`), with the headlines that support each point.

### Chunk 3: test each point against the data
- A small library of testers, one per kind, each a fixed query-builder recipe with sample floors:
  - **form**: last 10 innings / spells vs his previous two years (runs above average, economy)
  - **selection**: the player's numbers in the role/slot being talked about vs who he replaces
  - **matchup**: batter v bowler type, or v named bowler, with the shrinkage rule from matchup_edges.py
  - **conditions**: this ground / country, pace v spin, first v second innings, the last N matches here
  - **milestone / record**: distance to the mark, where it would rank
  - **tactics**: phase numbers (who bowls the powerplay, death overs, openers)
- Output a verdict (supported / not supported / partly / too little data) with the numbers and the query link.
  Untestable points (injuries, quotes about mood) are kept as context only.

### Chunk 4: "The storylines" chapter
- New first chapter in spec.CHAPTERS: 2-4 storyline cards. Each card: what's being said (headline, outlet, time,
  linked), what the data says (title states the finding in plain words), a small visual from the tester, and the
  verdict chip. Info sheet: all sources and the query.
- When there's no news (a quiet league game) the chapter is skipped and the preview is as today.

### Chunk 5: a lede, and the rest of the preview follows the story
- A 2-3 sentence intro at the top, written from the verified storylines only, through the same number guard the Reel
  scripts use (every number must appear in the tester outputs).
- Reorder: cards elsewhere in the preview that touch a storyline's player/team/phase get a relevance boost, so a story
  about NZ's spinners pulls the spin cards up.

### Chunk 6: social from the storylines
- The match-day IG post and X thread lead on the top storyline: a player and a number, which is what works
  (content rules: preview Reels that opened on a ground total flopped; ones that open on a player do better).
- Voiced v2 Reel from the storyline cards.

### Chunk 7: review gate and quality
- Admin view of each fixture's storylines with sources, verdicts and the generated lede; approve / drop / edit before
  the preview and the post use them. Recommended for the first few weeks, then optional.
- Log every talking point, verdict and whether it was kept, to tune the extraction prompt.

## Decisions (21 Oct 2026)

1. **Review gate:** the user approves each fixture's storylines in the admin before the preview or posts use them
   (chunk 7 moves ahead of chunk 4 going live). Revisit after a few weeks.
2. **Scope:** India, the top-10 men's sides and the major leagues. Everything else keeps today's preview.
3. **Sources on the site:** headline, outlet and link, never article text.
4. **Chunk 0 ships first,** today, ahead of the NZ v India T20I on 22 Oct.

## Tracker

| Chunk | Status |
|---|---|
| 0 Home page next big match | [x] 2026-10-21 |
| 1 News per fixture | [x] 2026-10-23: fixture_news in production (migration 025); .github/workflows/preview-news.yml at 02:37 and 11:07 IST; 60 headlines a fixture from ~30 outlets |
| 2 Talking points | [x] 2026-10-23: services/preview_storylines.py (one strong-model call a fixture, headlines only, each point tied to its headlines; players matched to the sides' XIs; Jev appeal, else headline count; top 5 pending), fixture_storylines (migration 028, production), twice a day in preview-news.yml |
| 3 Testers | [x] 2026-10-23: services/storyline_testers.py — form (last 10 innings / spells v the two years before; Primer runs above par in T20s, strike rate / economy in ODIs), matchup (head-to-head shrunk, or v pace / spin), tactics (the side's batting or bowling by phase), conditions (the ground's pace / spin), selection (his numbers, no verdict); a light model call says which way a claim points and whether it's batting or bowling, never a number. Tested on approve, on demand, and nightly (migration 030) |
| 4 Storylines chapter | [ ] |
| 5 Lede + reordering | [ ] |
| 6 Social from storylines | [ ] |
| 7 Review gate | [x] 2026-10-23: /admin/storylines (approve / edit = approve in your words / drop / undo; headlines per point; 'Find talking points' runs one fixture now); approved() is all a preview may read |
