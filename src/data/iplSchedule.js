import config from '../config';

export const fetchUpcomingMatches = async (count = 3) => {
  try {
    const response = await fetch(`${config.API_URL}/fixtures/upcoming?count=${count}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch fixtures: ${response.status}`);
    }

    const data = await response.json();
    return (Array.isArray(data) ? data : []).map((match, index) => ({
      matchNumber: index + 1,
      date: match.date,
      time: match.time,
      venue: match.venue,
      team1: match.team1,
      team2: match.team2,
      team1Abbr: match.team1_abbr,
      team2Abbr: match.team2_abbr,
    }));
  } catch (error) {
    console.error('Error fetching upcoming matches:', error);
    return [];
  }
};

export const formatDate = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  const options = { weekday: 'short', month: 'short', day: 'numeric' };
  return date.toLocaleDateString('en-US', options);
};

export const formatVenue = (venue) => venue || '';
