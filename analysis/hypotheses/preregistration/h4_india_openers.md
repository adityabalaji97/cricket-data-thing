# H4 — India's T20I openers are all or nothing

Common claim: Sanju Samson, Abhishek Sharma and Ishan Kishan, opening for India in T20Is, either
win the game or fail cheaply, with little in between.

* **Scope**: men's T20Is for India, 2015-01-01 to 2026-10-03; innings where the player batted at
  position 1 or 2 (`batting_position`). Batting view.
* **Unit**: an opening innings. Impact per innings (runs added to the team's projected total).
* **Comparison group**: every other India T20I opener in the same scope with at least 15 opening
  innings.
* **Primary effect ("all or nothing")**: the standard deviation of Impact per innings for the three
  (pooled) divided by the comparison group's. Claimed direction: above 1. Meaningful: 1.2.
  Bootstrap over innings.
* **Also reported**: share of innings with Impact below −5 ("fail") and above +10 ("fire") for each
  player and the comparison group; the full distribution (chart).
* **Win rate when they fail vs fire**: India's result in matches where one of the three opened,
  classed by that player's Impact (fail < −5, fire > +10; ties/no results excluded). Effect:
  win % (fire) − win % (fail), Fisher's exact test, bootstrap CI over innings. Also the player's
  WPA per innings by class.
* **Verdict**: on the primary effect; the win-rate split is context.
* **Minimum**: 15 opening innings per named player to report them individually.
