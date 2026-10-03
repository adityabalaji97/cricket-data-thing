# H5 — The anchor is dead

Common claim: a long, slow innings used to be useful in T20; now it loses games.

* **Scope**: men's T20, IPL and T20Is between the top 10 teams. Periods: 2015-01-01 to 2019-12-31
  and 2023-01-01 to 2026-10-03.
* **Unit**: a batting innings of 30+ balls faced (`batter_balls_faced:gte:30`), counting the whole
  innings.
* **Strike-rate buckets** (innings strike rate): under 110, 110-129.99, 130-149.99, 150+.
* **Outcomes**: the batting team's result (win % among decided matches) and the batter's WPA
  per innings (batting view).
* **Primary effect**: change between periods in the WPA per innings of the under-110 bucket
  relative to the 150+ bucket: (slow − fast) in 2023-26 minus (slow − fast) in 2015-19. Claimed
  direction: negative. Meaningful: −0.03 WPA per innings. Bootstrap over innings.
* **Secondary**: the same contrast in team win %.
* Context: share of 30+ ball innings that fall under 110 in each period.
* **Minimum**: 30 innings per bucket-period cell; cells under 15 are flagged.
