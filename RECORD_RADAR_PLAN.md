# Record radar: plan

Status: **signed off** (22 Oct 2026). Owner: Claude Code / Codex, one chunk per session.

## The problem

Accounts like @TheCricketPanda post lists the night of a match: "most powerplay sixes in T20I history", "50+ scores
for India chasing 200+", "50+ scores at SR 200+", "100 sixes at one batting position", "most runs in NZ v IND T20Is".
They get 100-200 likes in an hour. We have every one of these in the database, and more (rate, Impact, the context
behind the count), but nothing finds them for us.

## The idea

After every data load, run a fixed set of **record templates** for every player who just played (and everyone in the
next three days' fixtures), compare the leaderboard before and after the match, and surface what changed:

- **passed**: moved above a named player ("Abhishek passes Rohit: most powerplay sixes in T20Is")
- **entered**: into a top 10
- **milestone**: a round number (50 / 100 / 150...) on a template, and "Nth to X"
- **in reach** (before a match): a pass or milestone one good game away

Then draw what a list can't: the **rate** beside the count (innings or balls to get there, Impact), as a race chart
of running totals by innings, so "Abhishek passed Rohit" becomes "in 65 innings to Rohit's 141".

## Templates (each = a count, a scope, a condition)

| Family | Examples | Source |
|---|---|---|
| A. Ball counts | sixes / fours / runs / wickets / dots, by phase, batting position, v pace / spin, at a ground | query builder (delivery) |
| B. Innings counts | 50+ / 100s / 3-4-5 wicket hauls; while chasing, chasing 200+, at SR 200+, for a team, v a team | batting_stats / bowling_stats + match totals |
| C. Within-innings | 50 inside the powerplay, fastest 50s, most sixes in an innings | delivery running totals (idea_stats race/count_within) |
| D. Head to head | most runs / wickets / sixes in Team A v Team B games | query builder (teams) |
| E. Races | fastest to N by innings and balls | services/ig_posts/records.py (exists) |

Scopes: T20Is, each major league, a national team, a franchise, all men's T20s. Each template declares its sample
line so the card says exactly what was counted.

## Definitions we have to get right first (chunk 0)

Our numbers already differ from the screenshots' (22 Oct 2026), which is the risk in posting a record:

- **Powerplay sixes, T20Is**: we have Rohit 101, they have 98; Guptill 97 both; de Kock 87 and Karanbir 80 match.
  Partly explained (22 Oct): India v Australia, Nagpur, 23 Sep 2022 was an 8-over game with a 2-over powerplay;
  Rohit hit 3 sixes in overs 1-2 and one in over 3, which we count and they don't. Two more to find: other shortened
  games, or the 9 of his powerplay sixes from matches with no ball-by-ball detail (pre-2015).
- **Sixes at one batting position**: our Rohit at 1 (138) and Guptill (131) match; SKY at 4 is 111 for us, 116 for
  them. Their list leaves out Waseem at 2 (121), Munsey (116), Stirling (112) and Karanbir at 1 (200), so they appear to
  drop associates, but not consistently (Karanbir is in their powerplay list).
- **Batting position**: ours is the order batters first faced a ball (Cricsheet); a scorecard's order can differ for
  a batter who came in and faced nothing.
- **Coverage**: T20Is from 2005; any gaps against official totals listed per template.

Each template states its rule on the card (e.g. "overs 1-6; associates included") and a parity script compares our top
10s with reference lists we collect by hand, so a known gap is a footnote, not an error someone else finds.

## Rules

- Player and number first; the record is the hook, the rate is the deeper cut ([[content-rules]]).
- A record is only posted when its definition is on the card and its parity check passes or is footnoted.
- Associates are included and labelled; a "Full Members only" cut only when it changes the top 3.
- No blame, house vocabulary, card anatomy as everywhere.

## Chunks

### Chunk 0: definitions and parity (small, first)
- Explain Rohit 101 v 98 and SKY 111 v 116 from the data; decide the powerplay rule for shortened games.
- `scripts/record_parity.py`: our top 10 per template against hand-collected reference lists.

### Chunk 1: template registry + before/after for family A
- `services/record_radar.py`: templates as data; for a match, every template's leaderboard with end_date the day
  before and the day of; events (passed / entered / milestone).
- Test: Abhishek's powerplay sixes after 22 Oct 2026 yields "passed Rohit" (or reports the definition gap).

### Chunk 2: families B and C (innings counts, within-innings)
- 50+ while chasing 200+, at SR 200+, powerplay fifties; via batting_stats and delivery running totals.

### Chunk 3: family D and "in reach" before a fixture
- Head-to-head lists for the next fixtures; passes and milestones one game away (joins the preview's milestones card).

### Chunk 4: scoring and the queue
- Rank events by appeal (Jev), the player's profile and fixture relevance; at most N a day; drafts on the bench with
  a card and tweet text; the user picks in the admin at first.

### Chunk 5: cards
- Race chart (running total by innings, the passer and the passed highlighted) and ranked bars with the rate as
  each row's detail; one-tweet copy for X, a carousel when there's a story.

## Decisions (22 Oct 2026)

1. **Associates included**, labelled on the card.
2. **At most 3 radar drafts a day**, reviewed in the admin before anything is queued.
3. **Every competition** from the start (T20Is, every league in the data, all men's T20s).

## Tracker

| Chunk | Status |
|---|---|
| 0 Definitions + parity | [~] 2026-10-22: Rohit 101 v 98 was a namesake (Indonesia's Rohit Sharma, 3 powerplay sixes); radar splits 40 namesakes by national side (main side keeps the name; switchers, renamed sides, A sides and a swapped Bhutan v Bahrain match stay one person). Proper fix: Cricsheet player ids (next). Open: Waseem 96 v 95, SKY at 4 111 v 116 |
| 1 Registry + family A | [x] 2026-10-22: services/record_radar.py; one counts table per side (~25s) instead of the query builder (37s a leaderboard); floors: template's first milestone, positions 1-8, first 25 to a milestone; 14 Oct 2026 gave 22 events. Pace/spin templates wait (legacy pre-2015 balls have no bowling type) |
| 2 Families B, C | [ ] |
| 3 Family D + in reach | [ ] |
| 4 Scoring + queue | [x] 2026-10-22: score = kind x scope x template x fame (career runs/wickets); one per player; top 3 to the bench (source record-radar, post_by +3 days); associate sides' own lists weigh 0.45; runs after each nightly load (.github/workflows/record-radar.yml) |
| 5 Cards | [~] 2026-10-22: leaderboard card (top 8, the player in lime, passed / level marked); race chart and rates to do |
