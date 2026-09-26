// Per-browser state for the daily games: today's progress (so a refresh does not lose a game)
// and running stats with streaks. Keys are per game; everything is best-effort localStorage.

const key = (game, suffix) => `hindsight.daily.${game}.${suffix}`;

const read = (k, fallback) => {
  try {
    const raw = localStorage.getItem(k);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
};

const write = (k, value) => {
  try {
    localStorage.setItem(k, JSON.stringify(value));
  } catch {
    // Private mode or full storage: the game still works, it just will not persist.
  }
};

export const loadProgress = (game, date) => read(key(game, `day.v3.${date}`), null);
export const saveProgress = (game, date, progress) => write(key(game, `day.v3.${date}`), progress);

const EMPTY_STATS = { played: 0, currentStreak: 0, maxStreak: 0, lastPlayed: null, best: 0 };

const previousDay = (isoDate) => {
  const d = new Date(`${isoDate}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() - 1);
  return d.toISOString().slice(0, 10);
};

/** Stats as they stand today: a streak survives only if yesterday (or today) was played. */
export const loadStats = (game, today) => {
  const stats = { ...EMPTY_STATS, ...read(key(game, 'stats'), {}) };
  if (stats.lastPlayed && stats.lastPlayed !== today && stats.lastPlayed !== previousDay(today)) {
    stats.currentStreak = 0;
  }
  return stats;
};

/** Record a finished daily puzzle once; returns the updated stats. */
export const recordFinish = (game, date, score) => {
  const stats = { ...EMPTY_STATS, ...read(key(game, 'stats'), {}) };
  if (stats.lastPlayed === date) return stats; // already counted
  stats.played += 1;
  stats.currentStreak = stats.lastPlayed === previousDay(date) ? stats.currentStreak + 1 : 1;
  stats.maxStreak = Math.max(stats.maxStreak, stats.currentStreak);
  stats.best = Math.max(stats.best, score);
  stats.lastPlayed = date;
  write(key(game, 'stats'), stats);
  return stats;
};

/** "4h 12m" until the next puzzle (midnight IST). */
export const timeToNextPuzzle = (now = new Date()) => {
  const istNow = new Date(now.getTime() + 5.5 * 3600 * 1000);
  const next = new Date(Date.UTC(istNow.getUTCFullYear(), istNow.getUTCMonth(), istNow.getUTCDate() + 1));
  const ms = next.getTime() - istNow.getTime();
  const hours = Math.floor(ms / 3600000);
  const minutes = Math.floor((ms % 3600000) / 60000);
  return `${hours}h ${minutes}m`;
};
