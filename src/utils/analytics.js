/**
 * First-party product analytics (POST /events -> app_events; see routers/usage.py).
 *
 * Counts what people do -- page views, queries, shares, game plays -- so adoption can be
 * tracked week over week. It stores nothing personal: a random per-browser id (localStorage)
 * and a session id that expires after 30 idle minutes. Do Not Track is honoured, and every
 * failure is silent: analytics must never break the page.
 */
import config from '../config';

const ANON_KEY = 'hindsight.anon';
const SESSION_KEY = 'hindsight.session';
const SESSION_IDLE_MS = 30 * 60 * 1000;
const FLUSH_MS = 5000;

let queue = [];
let timer = null;

const randomId = () => {
  try {
    if (window.crypto?.randomUUID) return window.crypto.randomUUID();
  } catch {
    // fall through
  }
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
};

const disabled = () => {
  try {
    return navigator.doNotTrack === '1' || window.doNotTrack === '1';
  } catch {
    return false;
  }
};

const anonId = () => {
  try {
    let id = localStorage.getItem(ANON_KEY);
    if (!id) {
      id = randomId();
      localStorage.setItem(ANON_KEY, id);
    }
    return id;
  } catch {
    return 'no-storage';
  }
};

const sessionId = () => {
  try {
    const now = Date.now();
    const stored = JSON.parse(sessionStorage.getItem(SESSION_KEY) || 'null');
    const id = stored && now - stored.last < SESSION_IDLE_MS ? stored.id : randomId();
    sessionStorage.setItem(SESSION_KEY, JSON.stringify({ id, last: now }));
    return id;
  } catch {
    return null;
  }
};

const flush = () => {
  if (timer) {
    clearTimeout(timer);
    timer = null;
  }
  if (!queue.length) return;
  const events = queue.slice(0, 50);
  queue = queue.slice(50);
  const body = JSON.stringify({
    anon_id: anonId(),
    session_id: sessionId(),
    referrer: (document.referrer || '').slice(0, 200) || null,
    events,
  });
  try {
    fetch(`${config.API_URL}/events`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
      keepalive: true,
    }).catch(() => {});
  } catch {
    // ignore
  }
  if (queue.length) flush();
};

/** Record an event: snake_case name, optional small props object. */
export const track = (event, props) => {
  if (disabled()) return;
  queue.push({
    event,
    path: `${window.location.pathname}${window.location.search}`.slice(0, 200),
    props: props || undefined,
  });
  if (!timer) timer = setTimeout(flush, FLUSH_MS);
};

export const trackPageView = () => track('page_view');

if (typeof document !== 'undefined') {
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') flush();
  });
}
