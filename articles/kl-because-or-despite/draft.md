# KL: because of, or despite?

*A follow-up three and a half years in the making*

In May 2023 I wrote about the arguments that dragged me into cricket data, and one of them was KL Rahul. KL was well into his villain arc at the time. The charge sheet said he lacked intent, took too long to get going and left the batter at the other end to do the hitting. His defenders (of which I was one, admittedly) said he was batting that way to stop a collapse.

I ended that section with KL scoring 45 off 34 balls in an average innings, his team getting to about 165/5, and a question: *is this score achieved because of his contributions, or despite them?* I then said, and I quote, "that is outside the scope of this piece."

Well. It's in scope now.

## What changed

Back then I had two homemade metrics: Average Difference (batter average minus the team's average without him) and Strike Rate Difference (the same, for strike rate). They were crude. They didn't know what phase of the game it was, how many wickets were down or what the target was.

Hindsight now carries the metrics from Himanish Ganjoo's T20 Primer, which do exactly what I was reaching for, properly:

- **Runs above average (RAA):** the runs a batter scored, minus what an average batter would have scored from the same balls in the same situation (balls left, wickets down, the target). This is my old SR Difference, with the game state built in.
- **Wickets above average (WAA):** the same idea for dismissals. Positive means he got out less often than the situation would expect. This is my old Average Difference, grown up.
- **Impact:** how far the team's projected total moved while he batted. His runs count for it; his dismissals count against it, by how much they cost the rest of the innings. It is the honest answer to "because of, or despite?"

So, to settle the bet with 2023-me, I took every IPL batter who faced 600+ balls in one top-order slot between 2019 and 2023. That's KL's whole villain arc, and 20 batter-slots in all.

## The trade

![The trade](article/1.png)

There he is, top left, on his own.

From 2019 to 2023, KL scored **108 runs fewer than an average batter would have from the same balls** (RAA −6.2 per 100 balls). Only Virat Kohli, opening for RCB, was further behind. So the charge sheet wasn't wrong: in the situations he faced, KL scored slower than the game wanted.

But he also got out a lot less than anyone else. His **WAA was +49, more than double the next-best top-order batter** (Shikhar Dhawan, +23). He batted 42 balls per dismissal, the most of any of the 20.

Now look at the other corner. Prithvi Shaw scored +132 runs above average over the same period, the most on the chart, and gave away wickets doing it (WAA −10). He is KL's mirror image, and that's not a coincidence: it's the trade every opener makes, and these two made it from opposite ends.

The question is which end was worth more.

![Impact per innings](article/2.png)

**KL comes out 4th of 20 for Impact per innings (+2.3)**, behind Devon Conway, Mayank Agarwal and Suryakumar Yadav. Prithvi, for all those runs above average, is 15th (−0.3).

So: because of. The wickets KL saved were worth more than the runs he didn't score, and his defenders (hi) were right about *why* he was valuable.

I'd like to claim the full win for 2023-me. I can't, entirely. +2.3 runs an innings is good, not great: it's the same as Quinton de Kock. It's a tidy return for an opener who averaged 56. KL wasn't hurting his team; he was helping it a bit, in the least exciting way possible.

## Where the runs went

If KL was 108 runs behind the game over five seasons, I wanted to know where. The obvious suspect is the start of his innings, and the obvious suspect did it.

![First 10 balls](article/3.png)

In 2019–23 KL struck at about 103 in his first 10 balls of an innings, roughly 18 runs below par for every 100 balls. That's **about 104 of his 165 runs below par in those seasons**, from fewer than a third of his balls. After ball 10 he was close to an average-tempo batter: in three of those five seasons he struck at about 150 once he'd got through his first 10 balls.

And those first 10 balls weren't wasted: he was dismissed eight times in them in five seasons. That's the trade again, this time in miniature. He bought his start with runs.

## And the batter at the other end?

The 2023 charge sheet had one more count: that KL's slow starts put pressure on his partner. This one I could finally test.

![Partners](article/4.png)

With KL at the other end for Punjab and Lucknow, his partners scored below par in the powerplay (−5.7 per 100 balls) and above it in the middle overs (+7.2). The death overs look awful (−19.9), but that's only 307 balls, so I wouldn't read much into it.

The eagle-eyed amongst you have your pitchforks out already, and you're right. I can't tell from this whether the partners were scoring slowly *because of* KL or because KL's partners at Punjab were, well, Punjab's other openers. I tried comparing the same batters with and without him, and the samples got too small to say anything. Chris Gayle did fine with KL (+4.4 per 100 in the powerplay). Mayank Agarwal didn't (−5.9). Quinton de Kock was better with Rohit Sharma than with KL (+5.1 vs −0.8, though in 412 balls vs 142). Not enough to convict. Case adjourned.

## KL, 2024–26

![By season](article/5.png)

2023 was the only season he finished below zero, and it was his worst for almost everything: SR 113, 9 innings, −4.1 Impact an innings. It was also the first impact-player season. My theory, and it's only a theory, is that an extra batter makes a wicket cheaper, so a game built on not getting out was always going to lose value the moment the rules changed.

Then DC happened. In 2025 he bounced around the order (#3, #4, opening). The #4 experiment was the one that didn't work: −5.0 Impact an innings in six innings there, against +13 an innings in four at #3. In 2026 they opened with him, and this happened:

![IPL 2026](article/6.png)

**593 runs at a strike rate of 174, +66 Impact, 5th in the IPL.** His first 10 balls were at exactly par (SR 144), and after that he struck at 190.

One honest caveat. The "average" in RAA covers every season, and the impact-player years run hotter: IPL powerplays since 2023 come out at +8.4 runs per 100 balls against that average, from −2.8 before. So some of KL's 2026 number is just 2026. The fair comparison is with the other 20 batters who faced 250+ balls that season. They averaged +14 per 100 balls; KL was at +22, 6th of the 21. The only batters with more Impact were Vaibhav Sooryavanshi, Rajat Patidar, Virat Kohli and Ishan Kishan. That's not just the era. That's a batter who changed.

## So, because of or despite?

Because of, mostly. Just not for the reason either side was arguing about. KL never added runs by scoring them faster. He added them by not getting out, and for five years that was worth a little more than it cost. Then 2023 happened, the trade stopped paying, and by 2026 he'd changed how he batted. Somewhere a 2023 KL defender is quietly taking the credit.

If anyone's keeping score: me and the data, 1–1. I said he was batting that way for a reason, and he was. I also said he was fine, and he was only fine.

Speaking of Lucknow 2022–23: the mentor in that dressing room is the subject of my next piece.

---

*Every number here comes from Hindsight's query builder: ball-by-ball IPL data, men's T20. You can open the queries yourself:
[the 20 top-order slots, 2019–23](https://hindsightcricket.com/query?start_date=2019-01-01&end_date=2023-12-31&leagues=IPL&min_balls=600&metrics_perspective=batting&group_by=batter&group_by=batting_position&fmt=mens-t20) ·
[KL by season](https://hindsightcricket.com/query?leagues=IPL&batters=KL+Rahul&metrics_perspective=batting&group_by=season&fmt=mens-t20) ·
[KL's first 10 balls](https://hindsightcricket.com/query?start_date=2018-01-01&leagues=IPL&batters=KL+Rahul&metrics_perspective=batting&group_by=season&group_by=batter_ball_number_bucket&fmt=mens-t20) ·
[his partners](https://hindsightcricket.com/query?start_date=2018-01-01&end_date=2023-12-31&leagues=IPL&batting_teams=Kings+XI+Punjab&batting_teams=Punjab+Kings&batting_teams=Lucknow+Super+Giants&min_balls=150&exclude_batters=KL+Rahul&metrics_perspective=batting&group_by=non_striker&group_by=phase&fmt=mens-t20) ·
[IPL 2026](https://hindsightcricket.com/query?start_date=2026-01-01&leagues=IPL&min_balls=250&metrics_perspective=batting&group_by=batter&fmt=mens-t20)*

*Data: Hindsight (hindsightcricket.com); ball-by-ball tracking by Himanish Ganjoo & TechRadar; scorecards from Cricsheet. Impact, RAA and WAA follow Himanish Ganjoo's T20 Primer.*
