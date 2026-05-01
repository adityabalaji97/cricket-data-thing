-- Add day_or_night column to matches table
-- Classifies each match as 'day' or 'night'.
-- Heuristic (IPL-only for now): on a given (date, competition='IPL') group with
-- multiple matches, the row with the lower event_match_number is the day game,
-- the other(s) are night. Single matches default to 'night'.
-- Non-IPL leagues remain NULL until the heuristic is broadened.

ALTER TABLE matches
ADD COLUMN day_or_night VARCHAR(10);

ALTER TABLE matches
ADD CONSTRAINT day_or_night_check
CHECK (day_or_night IN ('day', 'night') OR day_or_night IS NULL);

-- Partial index. Most queries filter by 'day' (rarer); skip nulls to keep it small.
CREATE INDEX idx_matches_day_or_night
ON matches(day_or_night)
WHERE day_or_night IS NOT NULL;

-- Composite index supports the typical "venue + day_or_night + date range" filter
CREATE INDEX idx_matches_venue_day_or_night
ON matches(venue, day_or_night, date)
WHERE day_or_night IS NOT NULL;

COMMENT ON COLUMN matches.day_or_night IS 'Day vs night classification. IPL-only currently. Derived from event_match_number ordering within (date, competition) groups.';
