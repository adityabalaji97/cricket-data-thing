// The players, teams and venues this device opened last, newest first (the search page lists them). Kept in
// localStorage; storage that throws (private mode, blocked site data) just means no recents.
const KEY = 'hindsight.recentEntities';
const MAX = 8;

export const readRecentEntities = () => {
  try {
    const list = JSON.parse(localStorage.getItem(KEY) || '[]');
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
};

/** type: 'player' | 'team' | 'venue'. */
export const rememberEntity = (type, name) => {
  if (!name) return;
  try {
    const list = [{ type, name, at: Date.now() }, ...readRecentEntities().filter((e) => !(e.type === type && e.name === name))].slice(0, MAX);
    localStorage.setItem(KEY, JSON.stringify(list));
  } catch { /* storage off */ }
};
