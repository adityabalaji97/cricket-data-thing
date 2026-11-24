import config from '../config';

// Throws on a failed request, so the caller can tell "no fixtures" from "couldn't load them".
export const fetchUpcomingMatches = async (count = 3) => {
  const response = await fetch(`${config.API_URL}/fixtures/upcoming?count=${count}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch fixtures: ${response.status}`);
  }

  const data = await response.json();
  return (Array.isArray(data) ? data : []).map((match, index) => ({
    matchNumber: index + 1,
    matchId: match.match_id || null,
    date: match.date,
    time: match.time,
    startUtc: match.start_utc || null,
    venue: match.venue,
    series: match.series,
    format: match.format || 'T20',
    isLive: Boolean(match.is_live),
    status: match.status,
    statusText: match.status_text,
    team1: match.team1,
    team2: match.team2,
    team1Abbr: match.team1_abbr,
    team2Abbr: match.team2_abbr,
  }));
};

export const formatDate = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  const options = { weekday: 'short', month: 'short', day: 'numeric' };
  return date.toLocaleDateString('en-US', options);
};

export const formatVenue = (venue) => venue || '';
