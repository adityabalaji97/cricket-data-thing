# H3 — Shreyas Iyer is an anchor, not an accelerator

Common claim: in the middle overs Shreyas Iyer holds an innings together rather than speeding it
up, and he has a weakness against the short ball.

* **Scope**: men's T20, all competitions, 2024-01-01 to 2026-10-03. Batting view.
* **Players**: Shreyas Iyer; comparison group Suryakumar Yadav, Tilak Varma, Rinku Singh.
* **Middle overs**: overs 7-15 (0-indexed 6-14).
* **Unit**: a batting innings (balls in the middle overs of one innings). Bootstrap resamples
  innings.
* **Primary effect**: Iyer's middle-overs Impact per 100 balls minus the comparison group's pooled
  middle-overs Impact per 100 balls. Claimed direction: negative. Meaningful: −5 Impact per 100.
* **Secondary**: the same for strike rate (meaningful −10), separately against pace and against
  spin (exploratory).
* **Short balls**: lengths SHORT and SHORT_OF_A_GOOD_LENGTH (the feed's labels), all overs:
  Iyer's Impact per 100 and strike rate and dismissal rate vs the comparison group. Exploratory,
  as length is recorded for part of the balls only (coverage reported).
* **Verdict**: on the primary effect.
* **Minimum**: 300 middle-overs balls for Iyer and for each comparison player, else that player is
  dropped from the pooled group and the note says so.
