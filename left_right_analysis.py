# left_right_analysis.py
from sqlalchemy.sql import text
from database import get_database_connection

PACE_TYPES = ("RF", "RM", "RS", "LF", "LM", "LS")
SPIN_TYPES = ("RO", "RL", "LO", "LC")

def main():
    engine, SessionLocal = get_database_connection()
    session = SessionLocal()
    try:
        query = text(
            """
            WITH ball_data AS (
                SELECT
                    d.match_id,
                    d.innings,
                    d.batting_team,
                    p_striker.batter_type  AS striker_hand,
                    p_non.batter_type      AS non_striker_hand,
                    p_bowl.bowler_type,
                    d.runs_off_bat,
                    d.extras,
                    d.wicket_type
                FROM deliveries d
                JOIN players p_striker ON d.batter = p_striker.name
                JOIN players p_non     ON d.non_striker = p_non.name
                JOIN players p_bowl    ON d.bowler = p_bowl.name
            ),
            labelled AS (
                SELECT
                    match_id,
                    innings,
                    batting_team,
                    CASE
                        WHEN striker_hand IS NOT NULL
                         AND non_striker_hand IS NOT NULL
                         AND striker_hand != non_striker_hand
                        THEN 'L-R'
                        ELSE 'Same'
                    END AS hand_combo,
                    CASE
                        WHEN bowler_type IN :pace THEN 'pace'
                        WHEN bowler_type IN :spin THEN 'spin'
                        ELSE 'unknown'
                    END AS bowl_cat,
                    runs_off_bat + extras    AS total_runs,
                    runs_off_bat,
                    wicket_type
                FROM ball_data
            ),
            totals AS (
                SELECT
                    match_id,
                    innings,
                    batting_team,
                    COUNT(*) AS total_balls
                FROM labelled
                GROUP BY match_id, innings, batting_team
            )
            SELECT
                l.match_id,
                l.innings,
                l.batting_team,
                l.hand_combo,
                l.bowl_cat,
                COUNT(*)                              AS balls,
                SUM(total_runs)                       AS runs,
                SUM(CASE WHEN runs_off_bat IN (4,6) THEN 1 ELSE 0 END) AS boundaries,
                SUM(
                    CASE
                        WHEN wicket_type IS NOT NULL
                         AND wicket_type NOT IN ('run out','retired hurt','retired out')
                        THEN 1 ELSE 0
                    END
                ) AS wickets,
                ROUND(100.0 * COUNT(*) / t.total_balls, 2) AS pct_balls
            FROM labelled l
            JOIN totals t
              ON l.match_id = t.match_id
             AND l.innings  = t.innings
             AND l.batting_team = t.batting_team
            GROUP BY
                l.match_id, l.innings, l.batting_team,
                l.hand_combo, l.bowl_cat, t.total_balls
            ORDER BY l.match_id, l.innings, l.hand_combo, l.bowl_cat
            """
        )

        rows = session.execute(
            query,
            {"pace": PACE_TYPES, "spin": SPIN_TYPES}
        ).fetchall()

        for r in rows:

            average = {r.runs}.pop()/{r.wickets}.pop() if int({r.wickets}.pop()) > 0 else {r.runs}.pop()
            strikeRate = 100*{r.runs}.pop()/{r.balls}.pop() if int({r.balls}.pop()) > 0 else 0
            print(
                f"{r.match_id} | Inng {r.innings} | {r.batting_team:<4} | "
                f"{r.hand_combo}/{r.bowl_cat:<4} | "
                f"balls={r.balls:3d} ({r.pct_balls:5.2f}%), "
                f"runs={r.runs}, boundaries={r.boundaries}, wickets={r.wickets}, average={average}, strikeRate={strikeRate}"
            )

    finally:
        session.close()

if __name__ == "__main__":
    main()
