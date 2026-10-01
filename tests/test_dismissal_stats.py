from services import dismissal_stats as ds


def test_batter_sql_counts_striker_and_non_striker_outs_once_per_source():
    sql = ds._dismissal_rows_sql(ds.BATTER, "", "T20", "male")
    assert "dd.bat = ANY(:names)" in sql and "dd.non_striker = ANY(:names)" in sql
    # Non-striker branch only for modes that can dismiss the non-striker.
    assert "'run out', 'obstructing the field', 'retired out'" in sql
    # Legacy rows only for matches delivery_details does not hold.
    assert "NOT EXISTS (SELECT 1 FROM delivery_details x WHERE x.p_match = d.match_id)" in sql
    assert "retired not out (hurt)" in sql


def test_bowler_sql_uses_credited_wickets_and_format_phases():
    sql = ds._dismissal_rows_sql(ds.BOWLER, "", "T20", "male")
    assert "dd.bowl = ANY(:names)" in sql and "'run out'" not in sql
    assert "WHEN dd.over < 6 THEN 'powerplay' WHEN dd.over < 15 THEN 'middle' ELSE 'death'" in sql


def test_lbw_spellings_are_one_mode():
    assert "'leg before wicket' THEN 'lbw'" in ds._MODE_SQL.format(col="x")
