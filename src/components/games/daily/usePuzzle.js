import { useCallback, useEffect, useState } from 'react';
import config from '../../../config';
import { track } from '../../../utils/analytics';
import { loadProgress, loadStats } from './dailyStorage';

/**
 * Loads a daily or practice puzzle for a game and restores today's saved progress.
 * `practice()` switches to a fresh random puzzle (a new token); `daily()` goes back.
 */
export default function usePuzzle(game, path, emptyProgress) {
  const [puzzle, setPuzzle] = useState(null);
  const [progress, setProgress] = useState(null);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);
  const [token, setToken] = useState(null);

  const load = useCallback((nextToken) => {
    setPuzzle(null);
    setError(null);
    const query = nextToken ? `?puzzle=${nextToken}` : '';
    fetch(`${config.API_URL}${path}${query}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((data) => {
        const saved = data.daily ? loadProgress(game, data.puzzle) : null;
        setProgress(saved || emptyProgress(data));
        setStats(loadStats(game, data.today || data.puzzle));
        setPuzzle(data);
        if (!saved) track('game_start', { game, number: data.number, practice: !data.daily });
      })
      .catch(() => setError("Couldn't load the puzzle. Try again in a minute."));
  }, [game, path, emptyProgress]);

  useEffect(() => { load(token); }, [load, token]);

  return {
    puzzle, progress, setProgress, stats, setStats, error,
    practice: () => setToken(`p${Math.random().toString(36).slice(2, 10)}`),
    daily: () => setToken(null),
  };
}
