#!/usr/bin/env python3
"""
Backfill batting position and entry point data for batting_stats rows where NULL.

Uses delivery_details table to calculate:
- batting_position: order in which batter came to crease
- entry_overs: over number when batter entered
- entry_runs: team runs when batter entered  
- entry_balls: balls bowled when batter entered
"""

import logging
from sqlalchemy import text
from tqdm import tqdm
from database import get_database_connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_matches_needing_backfill(session, limit=None):
    """Get match_ids that have batting_stats with NULL batting_position."""
    query = """
        SELECT DISTINCT bs.match_id
        FROM batting_stats bs
        WHERE bs.batting_position IS NULL
        ORDER BY bs.match_id
    """
    if limit:
        query += f" LIMIT {limit}"
    result = session.execute(text(query))
    return [row[0] for row in result.fetchall()]


def get_match_deliveries_dd(session, match_id):
    """Get deliveries from delivery_details table."""
    query = text("""
        SELECT p_match as match_id, inns as innings, over, ball,
               bat as batter, team_bat as batting_team, score, wide
        FROM delivery_details
        WHERE p_match = :match_id
        ORDER BY inns, over, ball
    """)
    result = session.execute(query, {'match_id': match_id})
    columns = result.keys()
    return [dict(zip(columns, row)) for row in result.fetchall()]


def get_match_deliveries_legacy(session, match_id):
    """Get deliveries from legacy deliveries table."""
    query = text("""
        SELECT match_id, innings, over, ball,
               striker as batter, batting_team, 
               runs_off_bat + extras as score, wides as wide
        FROM deliveries
        WHERE match_id = :match_id
        ORDER BY innings, over, ball
    """)
    result = session.execute(query, {'match_id': match_id})
    columns = result.keys()
    return [dict(zip(columns, row)) for row in result.fetchall()]


def calculate_batting_position_data(match_id, innings, batter, deliveries):
    """Calculate batting position and entry point for a batter."""
    innings_dels = [d for d in deliveries if d['innings'] == innings]
    batter_dels = [d for d in innings_dels if d['batter'] == batter]
    
    if not batter_dels:
        return None
    
    # Find first ball faced
    first_ball = min(batter_dels, key=lambda x: (x['over'], x['ball']))
    
    # Count unique batters who batted before this one
    prior_batters = set()
    for d in innings_dels:
        if (d['over'], d['ball']) < (first_ball['over'], first_ball['ball']):
            prior_batters.add(d['batter'])
    
    batting_position = len(prior_batters) + 1
    
    # Entry point calculations
    entry_overs = first_ball['over'] + (first_ball['ball'] / 6.0)
    
    prior_dels = [d for d in innings_dels 
                  if (d['over'], d['ball']) < (first_ball['over'], first_ball['ball'])]
    entry_runs = sum(d['score'] or 0 for d in prior_dels)
    entry_balls = len([d for d in prior_dels if not d.get('wide')])
    
    return {
        'batting_position': batting_position,
        'entry_overs': round(entry_overs, 2),
        'entry_runs': entry_runs,
        'entry_balls': entry_balls
    }


def backfill_match(session, match_id):
    """Backfill batting position data for a single match."""
    # Try delivery_details first, fallback to legacy deliveries
    deliveries = get_match_deliveries_dd(session, match_id)
    source = 'delivery_details'
    
    if not deliveries:
        deliveries = get_match_deliveries_legacy(session, match_id)
        source = 'deliveries'
    
    if not deliveries:
        return {'updated': 0, 'skipped': 0, 'source': None}
    
    # Get batting_stats rows needing update for this match
    stats_query = text("""
        SELECT id, innings, striker 
        FROM batting_stats 
        WHERE match_id = :match_id AND batting_position IS NULL
    """)
    stats_rows = session.execute(stats_query, {'match_id': match_id}).fetchall()
    
    updated = 0
    skipped = 0
    
    for row in stats_rows:
        stat_id, innings, batter = row
        
        position_data = calculate_batting_position_data(match_id, innings, batter, deliveries)
        
        if position_data:
            update_query = text("""
                UPDATE batting_stats 
                SET batting_position = :batting_position,
                    entry_overs = :entry_overs,
                    entry_runs = :entry_runs,
                    entry_balls = :entry_balls
                WHERE id = :stat_id
            """)
            session.execute(update_query, {
                'stat_id': stat_id,
                'batting_position': position_data['batting_position'],
                'entry_overs': position_data['entry_overs'],
                'entry_runs': position_data['entry_runs'],
                'entry_balls': position_data['entry_balls']
            })
            updated += 1
        else:
            skipped += 1
    
    return {'updated': updated, 'skipped': skipped, 'source': source}


def backfill_batting_positions(limit=None, batch_size=100, dry_run=False):
    """Main function to backfill all NULL batting positions."""
    engine, SessionLocal = get_database_connection()
    session = SessionLocal()
    
    stats = {
        'matches_processed': 0,
        'rows_updated': 0,
        'rows_skipped': 0,
        'errors': 0,
        'from_dd': 0,
        'from_legacy': 0
    }
    
    try:
        match_ids = get_matches_needing_backfill(session, limit)
        logger.info(f"Found {len(match_ids)} matches needing batting position backfill")
        
        if dry_run:
            logger.info("DRY RUN - no changes will be made")
            # Just show stats
            sample = match_ids[:5]
            for mid in sample:
                result = backfill_match(session, mid)
                logger.info(f"  Match {mid}: would update {result['updated']} rows from {result['source']}")
            session.rollback()
            return stats
        
        for i, match_id in enumerate(tqdm(match_ids, desc="Backfilling positions")):
            try:
                result = backfill_match(session, match_id)
                stats['rows_updated'] += result['updated']
                stats['rows_skipped'] += result['skipped']
                stats['matches_processed'] += 1
                
                if result['source'] == 'delivery_details':
                    stats['from_dd'] += 1
                elif result['source'] == 'deliveries':
                    stats['from_legacy'] += 1
                
                # Commit in batches
                if (i + 1) % batch_size == 0:
                    session.commit()
                    logger.info(f"Committed batch {(i+1)//batch_size}, updated {stats['rows_updated']} rows so far")
                    
            except Exception as e:
                logger.error(f"Error processing match {match_id}: {e}")
                stats['errors'] += 1
                session.rollback()
        
        # Final commit
        session.commit()
        logger.info(f"Backfill complete!")
        logger.info(f"  Matches processed: {stats['matches_processed']}")
        logger.info(f"  Rows updated: {stats['rows_updated']}")
        logger.info(f"  Rows skipped: {stats['rows_skipped']}")
        logger.info(f"  From delivery_details: {stats['from_dd']}")
        logger.info(f"  From legacy deliveries: {stats['from_legacy']}")
        logger.info(f"  Errors: {stats['errors']}")
        
        return stats
        
    finally:
        session.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Backfill batting position data')
    parser.add_argument('--limit', type=int, help='Limit number of matches to process')
    parser.add_argument('--dry-run', action='store_true', help='Preview without making changes')
    parser.add_argument('--batch-size', type=int, default=100, help='Commit batch size')
    args = parser.parse_args()
    
    result = backfill_batting_positions(
        limit=args.limit, 
        batch_size=args.batch_size,
        dry_run=args.dry_run
    )
    
    print(f"\n✅ Done! Updated {result['rows_updated']} batting_stats rows")
