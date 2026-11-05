import { GROUP_WORDS, LENGTH_WORDS, LINE_WORDS, valueWords } from './qbWords';

// Reads a query's result the way a person would (QUERY_BUILDER_PLAN.md Q2): which measure the question is about,
// which picture fits the result's shape, the one sentence that answers it, and the rows to list under the chart.

const TIME = ['year', 'season'];
const RANKED = ['batter', 'bowler', 'venue', 'batting_team', 'bowling_team', 'partnership', 'non_striker', 'competition', 'country'];
const RANK_FLOOR = 30;   // balls a row needs to be ranked when the query sets no minimum

export const MEASURES = {
  strike_rate: { label: 'Strike rate', short: 'SR', format: 'int', better: 'higher' },
  economy: { label: 'Runs an over', short: 'an over', format: 'dec2', better: 'lower' },
  runs: { label: 'Runs', short: 'runs', format: 'int', better: 'higher' },
  average: { label: 'Average', short: 'avg', format: 'dec1', better: 'higher' },
  dot_percentage: { label: 'Dot %', short: 'dots', format: 'pct0', better: 'lower' },
  boundary_percentage: { label: 'Boundary %', short: 'boundaries', format: 'pct0', better: 'higher' },
  wickets: { label: 'Wickets', short: 'wkts', format: 'int', better: 'higher' },
};

export const fmtValue = (v, format) => {
  if (v == null || Number.isNaN(Number(v))) return '–';
  const n = Number(v);
  if (format === 'dec2') return n.toFixed(2);
  if (format === 'dec1') return n.toFixed(1);
  if (format === 'pct0') return `${Math.round(n)}%`;
  return Math.round(n).toLocaleString('en-US');
};

const economy = (r) => (r.economy != null ? Number(r.economy) : r.balls ? (6 * r.runs) / r.balls : null);
const metricOf = (r, key) => (key === 'economy' ? economy(r) : r[key] != null ? Number(r[key]) : null);

/** Batting or bowling: who the question is about. */
export const perspectiveOf = (filters, groupBy) => {
  const f = filters || {}; const g = groupBy || [];
  if (f.metrics_perspective === 'bowling') return 'bowl';
  if (f.metrics_perspective === 'batting') return 'bat';
  const bowlingSide = (f.bowlers || []).length || g.includes('bowler') || g.includes('bowling_team');
  const battingSide = (f.batters || []).length || g.includes('batter') || g.includes('batting_team') || g.includes('partnership');
  return bowlingSide && !battingSide ? 'bowl' : 'bat';
};

const measureFor = (perspective, groupBy) => {
  if ((groupBy || []).some((g) => ['match_id', 'innings', 'match_date'].includes(g))) return 'runs';
  return perspective === 'bowl' ? 'economy' : 'strike_rate';
};

/** A row's label from its group-by values, in plain words. */
export const rowLabel = (row, groupBy) => (groupBy || [])
  .map((g) => {
    const v = row[g];
    if (g === 'line') return LINE_WORDS[v] || v;
    if (g === 'length') return LENGTH_WORDS[v] || v;
    if (['bowl_kind', 'phase', 'wagon_zone', 'shot', 'bat_hand'].includes(g)) {
      const w = valueWords(g, v); return g === 'bowl_kind' ? w.replace(/^v /, '') : w;
    }
    return v == null || v === '' ? '–' : String(v);
  })
  .join(' · ');

const detailOf = (r, perspective) => {
  const parts = [`${Number(r.balls || 0).toLocaleString('en-US')} balls`];
  if (perspective === 'bowl') { if (r.wickets != null) parts.push(`${r.wickets} wkts`); } else if (r.wickets != null) parts.push(`${r.wickets} out`);
  if (r.dot_percentage != null) parts.push(`${Math.round(r.dot_percentage)}% dots`);
  return parts.join(' · ');
};

/** The subject in a few words, from the query's names ("Kohli", "IPL 2026 bowlers"). */
const subjectOf = (filters) => {
  const f = filters || {};
  const names = [...(f.batters || []), ...(f.players || []), ...(f.bowlers || [])];
  if (names.length === 1) return names[0];
  if (names.length === 2) return `${names[0].split(' ').slice(-1)[0]} and ${names[1].split(' ').slice(-1)[0]}`;
  const teams = [...(f.batting_teams || []), ...(f.bowling_teams || []), ...(f.teams || [])];
  if (teams.length === 1) return teams[0];
  if (f.venue) return `At ${f.venue}`;
  return null;
};

/**
 * The answer for a result: {type, measure, sentence:[[text, strong?]...], chart:{visual, payload}|null, rows, note}.
 * type: 'single' | 'time' | 'pitch' | 'ranked' | 'bars' | 'table'.
 */
export const ASKABLE = ['wickets', 'economy', 'strike_rate', 'average', 'dot_percentage', 'boundary_percentage'];

export const shapeAnswer = (data, filters, groupBy, measure = null) => {
  // A group with one value across every row (by batter when the question names one batter) says nothing: drop it.
  const g0 = groupBy || [];
  const g = g0.length > 1 ? g0.filter((k) => new Set((data || []).map((r) => r[k])).size > 1) : g0;
  const persp = perspectiveOf(filters, g0);
  const mKey = ASKABLE.includes(measure) ? measure : measureFor(persp, g);
  const M = MEASURES[mKey];
  const lowerBetter = M.better === 'lower';
  const all = (data || []).filter((r) => r && (r.balls || 0) > 0);
  const subject = subjectOf(filters);
  const S = (t, b = false) => [t, b];
  const val = (r) => fmtValue(metricOf(r, mKey), M.format);

  if (!all.length) return { type: 'empty', measure: mKey, sentence: [S('Nothing matched this question. Try widening the dates or removing a filter.')], rows: [] };

  // No grouping: one line of totals.
  if (!g.length) {
    const r = all[0];
    return {
      type: 'single', measure: mKey,
      sentence: [S(`${subject ? `${subject}: ` : ''}`), S(`${val(r)} ${M.short === 'SR' ? 'strike rate' : M.short}`, true),
        S(` from ${Number(r.balls).toLocaleString('en-US')} balls${persp === 'bowl' ? `, ${r.wickets} wickets` : `, ${r.runs} runs`}.`)],
      rows: [], tiles: r,
    };
  }

  // By year or season, alone: a line.
  if (g.length === 1 && TIME.includes(g[0])) {
    const rows = [...all].sort((a, b) => Number(a[g[0]]) - Number(b[g[0]]));
    const first = rows[0]; const last = rows[rows.length - 1];
    const peak = rows.reduce((p, r) => ((lowerBetter ? metricOf(r, mKey) < metricOf(p, mKey) : metricOf(r, mKey) > metricOf(p, mKey)) ? r : p), rows[0]);
    const sentence = rows.length === 1
      ? [S(`${subject ? `${subject}, ` : ''}${first[g[0]]}: `), S(val(first), true), S(` ${M.short === 'SR' ? 'strike rate' : M.short}.`)]
      : [S(`${subject ? `${subject}: ` : ''}${M.label.toLowerCase()} `), S(val(last), true), S(` in ${last[g[0]]}, from ${val(first)} in ${first[g[0]]}`),
        S(peak !== last && peak !== first ? `; ${lowerBetter ? 'lowest' : 'highest'} ${val(peak)} in ${peak[g[0]]}.` : '.')];
    return {
      type: 'time', measure: mKey, sentence,
      chart: rows.length > 1 ? {
        visual: 'metric_lines',
        payload: {
          x: { label: '', ticks: rows.map((r) => Number(r[g[0]])) },
          y: { label: M.label, format: M.format === 'dec2' ? 'dec1' : 'int', zero: false },
          series: [{ name: subject || M.label, points: rows.map((r) => ({ x: Number(r[g[0]]), y: Number(metricOf(r, mKey).toFixed(2)) })), highlight: true }],
        },
      } : null,
      rows: rows.map((r) => ({ label: String(r[g[0]]), detail: detailOf(r, persp), value: val(r), row: r })),
    };
  }

  // Line and length: a pitch map.
  if (g.length === 2 && g.includes('line') && g.includes('length')) {
    const cells = all.filter((r) => LINE_WORDS[r.line] && LENGTH_WORDS[r.length]);
    const balls = cells.reduce((s, r) => s + r.balls, 0);
    const mid = mKey === 'economy' ? (6 * cells.reduce((s, r) => s + r.runs, 0)) / Math.max(1, balls)
      : (100 * cells.reduce((s, r) => s + r.runs, 0)) / Math.max(1, balls);
    const big = [...cells].sort((a, b) => b.balls - a.balls);
    const floor = 15;
    const enough = cells.filter((r) => r.balls >= floor);
    const best = enough.reduce((p, r) => (!p || (lowerBetter ? metricOf(r, mKey) < metricOf(p, mKey) : metricOf(r, mKey) > metricOf(p, mKey)) ? r : p), null);
    const name = (r) => `${LINE_WORDS[r.line]}, ${LENGTH_WORDS[r.length].toLowerCase()}`;
    const sentence = [S(`${subject ? `${subject}: ` : ''}most balls on ${name(big[0])} (${big[0].balls}, ${val(big[0])} ${M.short === 'SR' ? 'SR' : M.short}).`)];
    if (best && best !== big[0]) sentence.push(S(` ${lowerBetter ? 'Cheapest' : 'Best'}: ${name(best)}, `), S(val(best), true), S('.'));
    return {
      type: 'pitch', measure: mKey, sentence,
      chart: {
        visual: 'pitch_map',
        payload: {
          hand: 'RHB', lines: ['WIDE_OUTSIDE_OFFSTUMP', 'OUTSIDE_OFFSTUMP', 'ON_THE_STUMPS', 'DOWN_LEG'],
          lengths: ['YORKER', 'FULL', 'GOOD_LENGTH', 'SHORT_OF_A_GOOD_LENGTH', 'SHORT'],
          metric: { label: M.label, format: M.format === 'dec2' ? 'dec1' : 'int', higher_better: !lowerBetter, mid: Number(mid.toFixed(2)) },
          min_balls: floor, show_outs: true,
          cells: cells.map((r) => ({ line: r.line, length: r.length, value: Number(metricOf(r, mKey).toFixed(2)), balls: r.balls, outs: r.wickets })),
        },
      },
      rows: big.slice(0, 5).map((r) => ({ label: name(r), detail: detailOf(r, persp), value: val(r), row: r })),
      note: `${floor}+ balls a cell`,
    };
  }

  // One ranked dimension: the ranked list is the picture.
  if (g.length === 1 && RANKED.includes(g[0])) {
    const floor = filters?.min_balls ? 0 : RANK_FLOOR;
    const pool = all.filter((r) => r.balls >= floor);
    const rows = [...(pool.length ? pool : all)].sort((a, b) => (lowerBetter ? metricOf(a, mKey) - metricOf(b, mKey) : metricOf(b, mKey) - metricOf(a, mKey)));
    const top = rows[0]; const second = rows[1];
    const what = GROUP_WORDS[g[0]] || g[0];
    const how = mKey === 'economy' ? ['is the cheapest', `${val(top)} an over`] : mKey === 'wickets' ? ['has the most wickets', val(top)]
      : [lowerBetter ? 'is lowest' : 'leads', `${M.label.toLowerCase()} ${val(top)}`];
    const sentence = [S(String(top[g[0]]), true), S(` ${how[0]}: ${how[1]}`),
      S(second ? `, then ${String(second[g[0]]).split(' ').slice(-1)[0]} (${val(second)}).` : '.')];
    return {
      type: 'ranked', measure: mKey, sentence,
      rows: rows.slice(0, 10).map((r, i) => ({ rank: i + 1, label: String(r[g[0]]), detail: detailOf(r, persp), value: val(r), num: metricOf(r, mKey), row: r })),
      note: `${rows.length} ${what}s${floor ? `, ${floor}+ balls` : ''} · ${lowerBetter ? 'lower is better' : 'higher is better'}`,
    };
  }

  // A few categories (phase, pace or spin, scoring zone, length...): bars.
  if (g.length === 1 && all.length <= 12) {
    const order = { powerplay: 0, middle: 1, death: 2 };
    const rows = [...all].sort((a, b) => (g[0] === 'phase' ? (order[a.phase] ?? 9) - (order[b.phase] ?? 9) : b.balls - a.balls));
    const best = rows.reduce((p, r) => ((lowerBetter ? metricOf(r, mKey) < metricOf(p, mKey) : metricOf(r, mKey) > metricOf(p, mKey)) ? r : p), rows[0]);
    const worst = rows.reduce((p, r) => ((lowerBetter ? metricOf(r, mKey) > metricOf(p, mKey) : metricOf(r, mKey) < metricOf(p, mKey)) ? r : p), rows[0]);
    const sentence = [S(`${subject ? `${subject}: ` : ''}${lowerBetter ? 'cheapest' : 'best'} ${M.short === 'SR' ? 'strike rate' : M.label.toLowerCase()} `),
      S(`${rowLabel(best, g).toLowerCase()} (${val(best)})`, true), S(best !== worst ? `, ${lowerBetter ? 'dearest' : 'lowest'} ${rowLabel(worst, g).toLowerCase()} (${val(worst)}).` : '.')];
    return {
      type: 'bars', measure: mKey, sentence,
      chart: {
        visual: 'metric_bars',
        payload: {
          metric: { label: M.label, format: M.format === 'dec2' ? 'dec2' : 'int' }, label_width: 130,
          rows: rows.map((r) => ({ name: rowLabel(r, g), value: Number(metricOf(r, mKey).toFixed(2)), detail: detailOf(r, persp), highlight: r === best })),
        },
      },
      rows: [],
    };
  }

  // Anything else (two dimensions, long lists): the rows, ranked by balls.
  const rows = [...all].sort((a, b) => b.balls - a.balls);
  return {
    type: 'table', measure: mKey,
    sentence: [S(`${rows.length} rows by ${g.map((x) => GROUP_WORDS[x] || x).join(' and ')}. The biggest: `), S(rowLabel(rows[0], g), true),
      S(`, ${val(rows[0])} ${M.short === 'SR' ? 'SR' : M.short} from ${rows[0].balls} balls.`)],
    rows: rows.slice(0, 12).map((r) => ({ label: rowLabel(r, g), detail: detailOf(r, persp), value: val(r), row: r })),
  };
};
