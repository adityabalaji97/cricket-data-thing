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

// A fixture's story preview: full team names (short codes like GG/MIE don't resolve), its format, its match id.
export const routePreview = (match) => (
  `/venue?venue=${encodeURIComponent(match.venue || '')}` +
  // Full names, as /links does: the preview can't resolve every short code (GG, MIE opened a venue-only page).
  `&team1=${encodeURIComponent(match.team1 || match.team1Abbr || '')}` +
  `&team2=${encodeURIComponent(match.team2 || match.team2Abbr || '')}` +
  `&includeInternational=true&topTeams=20&autoload=true&story=1` +
  // The preview is one format's record; ODI fixtures must open in ODI, not the global default.
  `&fmt=${match.format === 'ODI' ? 'mens-odi' : 'mens-t20'}` +
  `${match.matchId ? `&matchId=${encodeURIComponent(match.matchId)}` : ''}`
);

// Fixture start in the viewer's own time zone. The API's `date`/`time` are UTC, so without
// `startUtc` (an older cached response) the time is labelled UTC rather than guessed.
export const localStart = (match) => {
  if (!match.startUtc) {
    return { date: match.date, label: match.time ? `${match.time} UTC` : null };
  }
  const start = new Date(match.startUtc);
  const date = start.toLocaleDateString('en-CA');
  let time = start.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', timeZoneName: 'short' });
  // en-US browsers in India name the zone "GMT+5:30"; most of our readers know it as IST.
  const zone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  if (zone === 'Asia/Kolkata' || zone === 'Asia/Calcutta') time = time.replace(/GMT\+5:30$/, 'IST');
  const today = new Date().toLocaleDateString('en-CA');
  const tomorrow = new Date(Date.now() + 864e5).toLocaleDateString('en-CA');
  const day = date === today ? '' : date === tomorrow ? 'Tomorrow ' : `${start.toLocaleDateString(undefined, { weekday: 'short' })} `;
  return { date, label: `${day}${time}` };
};
