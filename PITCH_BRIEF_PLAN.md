# Morning pitch brief (replaces the automatic posts)

Agreed with the user on 1 Nov 2026, after two weeks in which none of the automatic posts were used and every
published post was hand-built.

## What we learned (18 Oct to 1 Nov 2026)

* **Every post that went out was hand-built and news-led:** Tilak, the 300th T20I, Naman Dhir, Vaibhav's first balls,
  Abhishek's twins, Hardik, India 259, Glenn Phillips.
* **The six that did well** (Reels 1.3k-1.9k views) each led with an Indian player and one surprising number: "not
  out in 21 chases, won all 21", "not one dot", "anyone like him?".
  * The two that dipped were a team-level India loss (819 views) and a New Zealand player with a metric name on the
    cover (441).
  * The user's read: Indian players are the draw.
* **The automatic posts weren't used:**
  * Trend posts repeat: the same Vaibhav post was queued five days running.
  * Previews were queued for every fixture (Namibia v Ireland, UAE v Oman).
  * The storylines (330 generated, none reviewed) were mostly duplicated news lines, not data angles.

## Decisions

1. **Audience: India first, then global.** India and IPL players lead. A non-Indian player gets in only for a historic
   run or as India's opponent, framed for an Indian audience.
2. **The pipeline stops making posts and makes pitches instead.**
   * Every morning, three pitches. Each one is a player, a number checked with the query builder, why now (a news
     link, last night's match, or a calendar date), a suggested picture, and a hook that follows the rules (player +
     plain number, no metric name).
   * The user picks one and Claude builds it by hand, as now.
3. **The automatic trend, preview, on-this-day, debate and play-along posts are switched off.** The code stays behind
   flags; their best angles feed the pitches.
4. **The brief lives at the top of the admin page** ("Today's pitches").

## Why the old trend and recap posts repeated (code review, 10 Nov 2026)

* **Trend posts (`services/ig_posts/trends.py`):**
  * Headlines chose who, never why: every player got the same recipe (his "most striking split", or "Is X the most
    complete batter?") whatever was being said about him.
  * No memory: the post's key was the player's name, so five days in the news made the same post five times.
  * Raw headline counts, so the perennial names stayed on top; nothing asked whether he was being talked about more
    than usual.
  * Three fixed scopes (IPL since 2023, T20Is since 2023, the ODI World Cup).
* **Recaps (`services/ig_posts/match.py`):** every match got the same slides in the same order (last meeting, win
  probability added, Impact with the bat, with the ball). Nothing asked what was unusual about this match, and it
  never decided a match wasn't worth a post.
* **Storylines:** 330 generated, none reviewed: too many, untested, in a queue that was a chore.

## Rules for the rebuild

1. **Carry the topic.** A pitch answers what is being said about the player (dropped, out of form, a matchup, a
   milestone), not a fixed recipe. The pieces exist for fixtures (`services/preview_storylines.py` turns headlines
   into claims, `services/storyline_testers.py` tests a claim against the data); wire them to players in the news.
2. **Spike, not volume.** Rank by today's mentions against the player's own trailing 14-day average, weighted
   India-first.
3. **Memory.** Every pitch is stored; no player + angle within 14 days. If he's in the news again, a new angle or no
   pitch.
4. **The most surprising number.** From the profile cards' "against typical" comparisons, on measures that repeat
   year to year (strike rate, economy, dot %, control %, shot and dismissal style); never wins added on a small
   sample.
5. **No pitch is a valid outcome.** A surprise bar; below it, nothing. Three pitches at most.
6. **A match gets one card or none.** The standout scanner (`services/standout_scanner.py`) already ranks a match's
   angles against history: the single best one, for India matches (and IPL in season), is the morning-after pitch.
7. **Pitches, not posts.** Three lines each: player, number, why now. The user picks; Claude builds by hand.

## Chunks

| # | Chunk | Status |
|---|---|---|
| P1 | Switch off the automatic trend, preview, on-this-day, debate and play-along posts (flags, default off); expire what's queued | [ ] |
| P2 | `post_pitches` table (day, rank, player, kind, angle, number, claim, why_now, source_url, visual, hook, status, picked_at) and a "Today's pitches" section at the top of the admin page with a Pick button | [ ] |
| P3a | **Who and why.** Headlines → players named (existing matcher) → spike score against a stored 14-day mention history (`player_mentions` by day) → one model call per top player: what is being said (kind + claim), from headlines only | [ ] |
| P3b | **The answer.** Per kind, a tester returns a verdict and one number: form (last 10 v his usual), matchup, selection (his slot's case from XI_BUILDER_PLAN.md X9), milestone (services/record_radar.py); else the most surprising stable number from his profile cards, related to the claim | [ ] |
| P3c | **Last night.** For India matches (IPL in season): the standout scanner's top angle and the India XI's "what moved" (XI_BUILDER_PLAN.md X9) as candidate pitches | [ ] |
| P3d | **Held ideas.** The backlog table in SOCIAL_CALENDAR.md and dated events as a third source when the news is quiet | [ ] |
| P4 | Ranking and checks: India-first, the 14-day player + angle rule, the surprise bar, hook rules (`social_rules.hook_problem`), numbers re-run on the morning shown | [ ] |
| P5 | Nightly run after the feed refresh; the picked pitch shows on the admin page for the build session | [ ] |
| P6 | **Review after two weeks:** how many pitches were picked, which sources they came from, how the posts did; drop sources nobody picks | [ ] |

## Open

* Reel insights for the last 8-10 Reels (skip rate or 3-second hold, average watch time, non-follower share, shares,
  saves, follows, post time) to test the "Indian players" read.
* The IPL 2027 squads (2026 auction buys, trades since) must be confirmed before the retention series.
