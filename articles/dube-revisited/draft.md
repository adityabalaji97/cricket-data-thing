# Dube, revisited

*I blamed the batting order. I was half right, and the other half was in my own table*

In June 2025 I wrote about Shivam Dube, or as I like to call him, Sir Benjamin Dubelliers. His 2025 numbers had dropped, and I set out to explain why. After bullying Claude for a while to get the scatter plots right, I landed on the batting order: in 2025 Dube was batting lower than in 2023, walking in at 57/3 and 75/4 instead of 95/1, with the top order already gone and fewer batters to come. I ended with a recommendation: Dube and Brevis at 4 and 5 for 2026.

Two things have happened since. Hindsight now carries Impact, runs above average and win probability, which can tell the difference between a batter playing badly and a batter playing in a bad situation. And IPL 2026 happened, so I can check whether CSK took my advice. (They did not read my article. I've made my peace with it.)

## 2025 wasn't the bad year

![Impact by season](article/1.png)

Dube struck at 132 in 2025, down from 162 the year before. That's the drop everyone saw, me included. But his **Impact, the runs he added to CSK's projected total, was +1.8 an innings in 2025, about the same as 2023's +1.7** and nearly double 2024's.

Impact can say that because it knows what the score was when he walked in. And this is where 2025-me gets a point back.

![Pressure](article/2.png)

Leverage measures how much a ball can swing the result. The game's average is about 0.1. **Dube's balls in 2025 averaged 0.16, nearly twice his 2023 (0.09).** That's 57/3 in a number. He batted in the tightest spots of his CSK career, and in them he added more win probability (+0.65 of a win across the season) than in any other year at CSK. In 2023, the title year, it was −0.33.

So the batting order argument holds, sort of. He was batting in harder situations, and the strike rate fell because of it. But he wasn't failing in them. If anything, 2025 was his most useful season at CSK.

If anyone's keeping score: 1–0 to me. Don't get used to it.

## The part I didn't look at

Here is the table from last year's piece, the one with his numbers against pace and spin. Against spin in 2025 he averaged 65 and struck at 122.6, and I mentioned it, and then I moved straight on to batting positions. That was the bigger story, and it was sitting in my own screenshot.

![Spin](article/3.png)

Runs above average is adjusted for the game state, so this isn't about where he batted. **Against off-spin he went from 39 runs above par per 100 balls in 2023 to 17 below in 2025.** Against wrist-spinners with a googly, +42 to −14. And against pace he got *better*, from −17 to +3.

The off-spin bit made me laugh, because I've written about this before. Dube is left-handed, so off-spin turns away from him: exactly the "traditional" matchup my left-right piece tested, the one where the three lowest strike rates belonged to the ball leaving the bat. In 2023 Dube didn't care. In 2025 he did. The shots tell the same story: his drives against spin went at a strike rate of 200 in 2023, with ten sixes, and 137 in 2025, with five.

So: 1–1. The batting order explained the strike rate. It didn't explain the spin.

## Teams have noticed, twice

![Spin share](article/4.png)

There's a pattern here that's almost funny. When Dube murders spin, teams stop bowling it to him. 45% of his balls came from spinners in 2023, the year he hit them for 22 sixes. In 2024 it was 23%. Then in 2025, with the spin numbers falling, it went back up to 43%, and in 2026 it dropped again, to 19%, 33 balls all season.

That's what a reputation looks like in data.

## And my advice for 2026?

![Batting order 2026](article/5.png)

I said Dube and Brevis at 4 and 5. In 2026 **Dube batted at 4 in three of his twelve innings.** He batted at 6 five times and at 7 four times. Brevis did bat at 5 in five innings, and struck at 136 for an Impact of −2.8 an innings, after three innings at 5 in 2025 that went at 202. These are tiny samples, a handful of innings each, so I'm not going to pretend this proves anything about either of them.

What it does show is that 2026 was the actual bad season. Dube's Impact went to −1.4 an innings, the first time below zero in his CSK years, with almost no spin to hit and most of his innings starting at 6 or 7.

## Meanwhile, for India

The odd thing is that the best Dube of the last two years hasn't been at CSK at all. In 38 T20I innings since Gautam Gambhir took over, he has 743 runs at a strike rate of 159 and **+2.2 Impact an innings**, more than any season he's had in yellow. He's also bowled 63 overs for 29 wickets, at 10.3 an over. That's the sixth-bowler job, and costly, but it's an option: in [my piece on Gambhir's teams](https://hindsightcricket.com/notes/gambhirs-xi), that's exactly the kind of player he picks.

## So

2025-me said Dube was batting too low, too late, with too little support. The numbers say that was true, and that he did fine anyway. What 2025-me missed was the spin, which was right there in his own table. 2026 was the real dip, and CSK didn't try the fix.

Much like last time, I still don't know how to write a satisfying conclusion. So I'll just say this: CSK, if you're reading, 4 and 5. I'm not asking again.

---

*Every number here comes from Hindsight's query builder, men's T20, batting view: [Dube by season](https://hindsightcricket.com/query?start_date=2022-01-01&leagues=IPL&batters=Shivam+Dube&metrics_perspective=batting&group_by=season&fmt=mens-t20) · [pace and spin](https://hindsightcricket.com/query?start_date=2022-01-01&leagues=IPL&batters=Shivam+Dube&metrics_perspective=batting&group_by=season&group_by=bowl_kind&fmt=mens-t20) · [by spin type](https://hindsightcricket.com/query?start_date=2022-01-01&leagues=IPL&batters=Shivam+Dube&bowl_kind=spin+bowler&metrics_perspective=batting&group_by=season&group_by=bowl_style&fmt=mens-t20) · [shots against spin](https://hindsightcricket.com/query?start_date=2023-01-01&end_date=2025-12-31&leagues=IPL&batters=Shivam+Dube&bowl_kind=spin+bowler&metrics_perspective=batting&group_by=season&group_by=shot_family&fmt=mens-t20) · [2025–26 batting positions](https://hindsightcricket.com/query?start_date=2025-01-01&leagues=IPL&batters=Shivam+Dube&batters=Dewald+Brevis&metrics_perspective=batting&group_by=batter&group_by=season&group_by=batting_position&fmt=mens-t20) · [India batting](https://hindsightcricket.com/query?start_date=2024-07-27&batters=Shivam+Dube&include_international=true&metrics_perspective=batting&group_by=batter&fmt=mens-t20) · [India bowling](https://hindsightcricket.com/query?start_date=2024-07-27&bowlers=Shivam+Dube&include_international=true&metrics_perspective=bowling&group_by=bowler&fmt=mens-t20)*

*Data: Hindsight (hindsightcricket.com); ball-by-ball tracking by Himanish Ganjoo & TechRadar; scorecards from Cricsheet. Impact, RAA, WPA and leverage follow Himanish Ganjoo's T20 Primer.*
