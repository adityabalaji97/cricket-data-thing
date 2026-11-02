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

## Chunks

| # | Chunk | Status |
|---|---|---|
| P1 | Switch off the automatic trend, preview, on-this-day, debate and play-along posts (flags, default off); expire what's queued | [ ] |
| P2 | `post_pitches` table (day, rank, player, number, claim, why_now, source_url, visual, hook, status, picked_at) and a "Today's pitches" section on the admin page with a Pick button | [ ] |
| P3 | Pitch sources: (a) last night's standouts by Impact/WPA, with career detectors (best stretch, career best, first time); (b) news storylines, deduped and tested against the data (services/storyline_testers.py); (c) calendar and held ideas (SOCIAL_CALENDAR.md, held posts) | [ ] |
| P4 | Ranking and checks: India-first score, no player+angle repeated within 14 days, hook rules (social_rules.hook_problem), numbers re-run on the morning the pitch is shown | [ ] |
| P5 | Run it in the nightly workflow after the feed refresh; the picked pitch shows on the admin page for the build session | [ ] |

## Open

* Reel insights for the last 8-10 Reels (skip rate or 3-second hold, average watch time, non-follower share, shares,
  saves, follows, post time) to test the "Indian players" read.
* The IPL 2027 squads (2026 auction buys, trades since) must be confirmed before the retention series.
