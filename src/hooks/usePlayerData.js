import { useState, useCallback } from 'react';
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

  const fetchAllData = useCallback(async () => {
    if (!playerName) return;

    setLoading(true);
    setError(null);
    const params = buildParams();

    const fetches = [];

    // Always try batting stats
    fetches.push(
      fetch(`${config.API_URL}/player/${encodeURIComponent(playerName)}/stats?${params}`)
        .then(r => r.ok ? r.json() : null)
        .then(data => setBattingStats(data))
        .catch(() => setBattingStats(null))
    );

    // Always try batting ball stats
    fetches.push(
      fetch(`${config.API_URL}/player/${encodeURIComponent(playerName)}/ball_stats?${params}`)
        .then(r => r.ok ? r.json() : null)
        .then(data => {
          if (data) {
            setBattingStats(prev => prev ? { ...prev, ball_by_ball_stats: data.ball_by_ball_stats || [] } : null);
          }
        })
        .catch(() => {})
    );

    // Always try bowling stats
    fetches.push(
      fetch(`${config.API_URL}/player/${encodeURIComponent(playerName)}/bowling_stats?${params}`)
        .then(r => r.ok ? r.json() : null)
        .then(data => setBowlingStats(data))
        .catch(() => setBowlingStats(null))
    );

    // Batter dismissal stats
    fetches.push(
      fetch(`${config.API_URL}/players/${encodeURIComponent(playerName)}/dismissal_stats?${params}`)
        .then(r => r.ok ? r.json() : null)
        .then(data => setDismissalStats(data))
        .catch(() => setDismissalStats(null))
    );

    // Bowler dismissal stats
    fetches.push(
      fetch(`${config.API_URL}/players/${encodeURIComponent(playerName)}/bowling_dismissal_stats?${params}`)
        .then(r => r.ok ? r.json() : null)
        .then(data => setBowlingDismissalStats(data))
        .catch(() => setBowlingDismissalStats(null))
    );

    try {
      await Promise.all(fetches);
    } catch (e) {
      setError('Failed to load player data');
      console.error('Error fetching player data:', e);
    } finally {
      setLoading(false);
    }
  }, [playerName, buildParams]);

  return {
    battingStats,
    bowlingStats,
    dismissalStats,
    bowlingDismissalStats,
    playerType,
    loading,
    error,
    fetchPlayerType,
    fetchAllData
  };
};

export default usePlayerData;
