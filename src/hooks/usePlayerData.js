import { useState, useCallback, useRef } from 'react';
import config from '../config';

/**
 * Custom hook to fetch all player data (batting + bowling + dismissals + type detection)
 */
const usePlayerData = (playerName, dateRange, selectedVenue, competitionFilters) => {
  const [battingStats, setBattingStats] = useState(null);
  const [bowlingStats, setBowlingStats] = useState(null);
  const [dismissalStats, setDismissalStats] = useState(null);
  const [bowlingDismissalStats, setBowlingDismissalStats] = useState(null);
  const [playerType, setPlayerType] = useState(null);
  const [loading, setLoading] = useState(false);
  const [dismissalLoading, setDismissalLoading] = useState(false);
  const [error, setError] = useState(null);

  const buildParams = useCallback(() => {
    const params = new URLSearchParams();
    if (dateRange?.start) params.append('start_date', dateRange.start);
    if (dateRange?.end) params.append('end_date', dateRange.end);
    if (selectedVenue && selectedVenue !== "All Venues") params.append('venue', selectedVenue);
    if (competitionFilters?.leagues) {
      competitionFilters.leagues.forEach(league => params.append('leagues', league));
    }
    if (competitionFilters?.international) {
      params.append('include_international', competitionFilters.international);
      if (competitionFilters.topTeams) {
        params.append('top_teams', competitionFilters.topTeams);
      }
    }
    return params;
  }, [dateRange, selectedVenue, competitionFilters]);

  const fetchPlayerType = useCallback(async () => {
    if (!playerName) return;
    try {
      const res = await fetch(`${config.API_URL}/players/${encodeURIComponent(playerName)}/player_type`);
      if (res.ok) {
        const data = await res.json();
        setPlayerType(data);
      }
    } catch (e) {
      console.error('Error fetching player type:', e);
    }
  }, [playerName]);

  // Each fetch carries the id of the request that started it, so a slow response for the previous
  // player or filters can't land on top of the current one.
  const requestId = useRef(0);

  const fetchAllData = useCallback(async () => {
    if (!playerName) return;

    const id = ++requestId.current;
    const current = () => id === requestId.current;
    const params = buildParams();
    const name = encodeURIComponent(playerName);
    const getJson = (path) => fetch(`${config.API_URL}${path}?${params}`)
      .then(r => (r.ok ? r.json() : null))
      .catch(() => null);

    setLoading(true);
    setDismissalLoading(true);
    setError(null);
    setBattingStats(null);
    setBowlingStats(null);
    setDismissalStats(null);
    setBowlingDismissalStats(null);

    // Dismissals feed a section well down the page, and the batting one is the slowest call
    // (1.6-1.8s on production). They load alongside but no longer hold up the first screen.
    Promise.all([
      getJson(`/players/${name}/dismissal_stats`).then(d => { if (current()) setDismissalStats(d); }),
      getJson(`/players/${name}/bowling_dismissal_stats`).then(d => { if (current()) setBowlingDismissalStats(d); }),
    ]).finally(() => { if (current()) setDismissalLoading(false); });

    const battingP = getJson(`/player/${name}/stats`);
    const ballP = getJson(`/player/${name}/ball_stats`);
    const bowlingP = getJson(`/player/${name}/bowling_stats`);

    // Merge ball-by-ball stats once both have landed: merging into whatever state existed when
    // ball_stats arrived lost them whenever it beat /stats.
    const batting = Promise.all([battingP, ballP]).then(([stats, balls]) => {
      if (!current()) return;
      setBattingStats(stats ? { ...stats, ball_by_ball_stats: balls?.ball_by_ball_stats || [] } : null);
    });
    const bowling = bowlingP.then(d => { if (current()) setBowlingStats(d); });

    try {
      await Promise.all([batting, bowling]);
    } catch (e) {
      if (current()) setError('Failed to load player data');
      console.error('Error fetching player data:', e);
    } finally {
      if (current()) setLoading(false);
    }
  }, [playerName, buildParams]);

  return {
    battingStats,
    bowlingStats,
    dismissalStats,
    bowlingDismissalStats,
    playerType,
    loading,
    dismissalLoading,
    error,
    fetchPlayerType,
    fetchAllData
  };
};

export default usePlayerData;
