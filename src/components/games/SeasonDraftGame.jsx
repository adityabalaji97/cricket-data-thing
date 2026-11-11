import React, { useEffect, useMemo, useState } from 'react';
import { Box, Drawer } from '@mui/material';
import { useLocation, useNavigate } from 'react-router-dom';
import config from '../../config';
import { colors, fonts } from '../../theme/hindsightDark';
import {
  BUDGET, COST_MIN, OVERSEAS_MAX, SLOTS, bestFromDeal, checkPicks, costOf, costTable, deal, profile, seasonResults,
} from '../../utils/draftEngine';

// Season Draft (XI_BUILDER_PLAN.md X10): fill eleven slots in any order from IPL player-seasons, five dealt per slot,
// under a budget (a card's cost from how far above his season he was and how much he played) and four overseas.
// Then the XI plays all 19 IPL seasons (simulated, era-adjusted): "made the playoffs in N of 19" is the game's rule,
// not a prediction. Every draft gets its own deal (d); the deal and the picks (p) live in the URL, so a draft is a link.

const mono = { fontFamily: fonts.mono, fontVariantNumeric: 'tabular-nums' };
const UNIT = { openers: 'avg', top: 'SR', finishers: 'SR', pp_pace: 'wkts / 4 ov', mid_spin: 'wkts / 4 ov', death_pace: 'an over' };
const LABEL = { openers: 'opening', top: 'at 3-4', finishers: 'at 5-7', pp_pace: 'powerplay', mid_spin: 'middle overs', death_pace: 'death' };
const fmtV = (k, v) => (k === 'openers' ? v.toFixed(1) : k === 'top' || k === 'finishers' ? v.toFixed(0) : v.toFixed(2));
const newDeal = () => Math.random().toString(36).slice(2, 10);

const CardRow = ({ card, slot, cost, onPick, why }) => (
  <Box component="button" type="button" disabled={!!why} onClick={onPick}
    sx={{ all: 'unset', cursor: why ? 'default' : 'pointer', opacity: why ? 0.45 : 1, display: 'block', bgcolor: colors.surface1,
      border: `1px solid ${colors.border}`, borderRadius: '14px', px: 1.5, py: 1.1, '&:hover': { borderColor: why ? colors.border : colors.accent } }}>
    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 1 }}>
      <Box sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 18, minWidth: 0, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
        {`${card.name} ${card.season}`}
      </Box>
      <Box sx={{ ...mono, fontSize: 15, color: colors.accent, whiteSpace: 'nowrap' }}>{`${cost} cr`}</Box>
    </Box>
    <Box sx={{ fontSize: 11.5, color: colors.textLo }}>{[card.team, card.overseas ? 'overseas' : null, why].filter(Boolean).join(' · ')}</Box>
    {slot.roles.filter((r) => card.roles[r]).map((r) => {
      const x = card.roles[r];
      const good = r === 'death_pace' ? x.r < 1 : x.r > 1;
      return (
        <Box key={r} sx={{ display: 'flex', justifyContent: 'space-between', gap: 1, mt: 0.3, fontSize: 13 }}>
          <Box sx={{ color: colors.textMed, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{`${fmtV(r, x.v)} ${UNIT[r]} ${LABEL[r]} · ${x.balls}b`}</Box>
          <Box sx={{ ...mono, whiteSpace: 'nowrap', color: good ? colors.accent : colors.textLo }}>{`${x.r.toFixed(2)}×`}</Box>
        </Box>
      );
    })}
  </Box>
);

const Strip = ({ results }) => (
  <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(52px, 1fr))', gap: 0.75 }}>
    {results.map((r) => (
      <Box key={r.season} title={`${r.season}: ${r.rank} of ${r.of}, won ${r.wins} of ${r.games}`}
        sx={{ textAlign: 'center', borderRadius: '8px', py: 0.6, ...mono, fontSize: 12.5,
          bgcolor: r.topped ? '#c9a227' : r.made ? colors.accent : colors.surface2, color: r.made ? colors.bg : colors.textLo }}>
        {r.season.slice(-2)}
        <Box sx={{ fontSize: 10, opacity: 0.8 }}>{`#${r.rank}`}</Box>
      </Box>
    ))}
  </Box>
);

const SeasonDraftGame = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const q = new URLSearchParams(location.search);
  const d = q.get('d');
  const pStr = (q.get('p') || '').padEnd(SLOTS.length, '-').slice(0, SLOTS.length);
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);
  const [open, setOpen] = useState(null);  // the slot whose cards are showing
  useEffect(() => {
    document.title = 'Season Draft · Hindsight';
    fetch(`${config.API_URL}/games/season-draft/data`).then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then(setData).catch(() => setError(true));
  }, []);
  // A new draft gets its own deal, written into the URL so the draft is a link.
  useEffect(() => { if (!d) navigate({ search: `?d=${newDeal()}` }, { replace: true }); }, [d, navigate]);
  const dealt = useMemo(() => (data && d ? deal(data.cards, `season-draft-${d}`) : null), [data, d]);
  const table = useMemo(() => (data ? costTable(data.cards) : null), [data]);
  // Picks from the URL ('-' an empty slot, else the card's index), kept only while they fit the rules.
  const picks = useMemo(() => {
    if (!dealt) return [];
    const out = Array(SLOTS.length).fill(null);
    pStr.split('').forEach((ch, i) => {
      const card = /[0-9]/.test(ch) ? dealt[i]?.[Number(ch)] : null;
      if (!card) return;
      const trial = out.slice(); trial[i] = card;
      if (checkPicks(trial, table).ok) out[i] = card;
    });
    return out;
  }, [dealt, pStr, table]);
  const filled = picks.filter(Boolean).length;
  const done = !!dealt && filled === SLOTS.length;
  const results = useMemo(() => (done ? seasonResults(profile(picks), data.seasons, data.roles, `${d}|${pStr}`) : null), [done, picks, data, d, pStr]);
  const best = useMemo(() => (done ? seasonResults(profile(bestFromDeal(dealt, data.roles, table)), data.seasons, data.roles, `${d}|best`) : null), [done, dealt, data, d, table]);

  if (error) return <Box sx={{ p: 2, color: colors.textLo }}>The draft couldn't load just now. Try again shortly.</Box>;
  if (!dealt) return <Box sx={{ p: 2, color: colors.textLo }}>Dealing…</Box>;
  const state = checkPicks(picks, table);
  const made = results ? results.filter((r) => r.made).length : 0;
  const setPick = (slot, idx) => {
    const chars = pStr.split(''); chars[slot] = idx == null ? '-' : String(idx);
    navigate({ search: `?d=${d}&p=${chars.join('')}` }, { replace: true });
    setOpen(null);
  };
  // Why a card can't go in a slot: already picked, the overseas cap, or the budget (keeping the cheapest possible
  // cost for each other empty slot, so the XI can always be finished).
  const why = (card, slot) => {
    const others = picks.map((c, i) => (i === slot ? null : c));
    if (others.some((c) => c && c.name === card.name)) return 'already in your XI';
    const st = checkPicks(others, table);
    if (card.overseas && st.overseas >= OVERSEAS_MAX) return 'four overseas already';
    const empty = others.filter((c, i) => !c && i !== slot).length;
    if (costOf(card, slot, table) > st.left - COST_MIN * empty) return 'over the budget';
    return null;
  };

  return (
    <Box sx={{ maxWidth: 560, mx: 'auto', px: 2, pt: 1.5, pb: 4, color: colors.textHi, display: 'flex', flexDirection: 'column', gap: 1.5 }}>
      <Box>
        <Box sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 26 }}>Season Draft</Box>
        <Box sx={{ color: colors.textMed, fontSize: 13.5 }}>Fill eleven slots from IPL player-seasons, in any order, on a budget. Would your XI have made the playoffs?</Box>
      </Box>

      <Box sx={{ display: 'flex', gap: 1 }}>
        {[[`${state.left}`, `of ${BUDGET} credits left`], [`${state.overseas}/${OVERSEAS_MAX}`, 'overseas'], [`${filled}/11`, 'picked']].map(([v, l]) => (
          <Box key={l} sx={{ flex: 1, bgcolor: colors.surface1, border: `1px solid ${colors.border}`, borderRadius: '12px', px: 1.25, py: 0.9 }}>
            <Box sx={{ ...mono, fontSize: 19 }}>{v}</Box>
            <Box sx={{ fontSize: 11, color: colors.textLo }}>{l}</Box>
          </Box>
        ))}
      </Box>

      <Box sx={{ bgcolor: colors.surface1, border: `1px solid ${colors.border}`, borderRadius: '14px', px: 1.25, py: 0.5 }}>
        {SLOTS.map((slot, i) => {
          const c = picks[i];
          return (
            <Box key={i} component="button" type="button" onClick={() => setOpen(i)}
              sx={{ all: 'unset', cursor: 'pointer', boxSizing: 'border-box', display: 'grid', gridTemplateColumns: '84px 1fr auto', alignItems: 'center', gap: 1,
                py: 0.9, width: '100%', borderTop: i ? `1px solid ${colors.border}` : 'none' }}>
              <Box sx={{ fontSize: 12, color: colors.textLo, whiteSpace: 'nowrap' }}>{slot.label}</Box>
              <Box sx={{ fontSize: 14.5, minWidth: 0, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', color: c ? colors.textHi : colors.accent }}>
                {c ? `${c.name} ${c.season}` : 'Pick'}
                {c?.overseas && <Box component="span" sx={{ fontSize: 11, color: colors.textLo }}> · overseas</Box>}
              </Box>
              <Box sx={{ ...mono, fontSize: 13, color: colors.textMed }}>{c ? `${costOf(c, i, table)}` : ''}</Box>
            </Box>
          );
        })}
      </Box>

      {!done && (
        <Box sx={{ fontSize: 11.5, color: colors.textLo }}>
          Tap any slot to see its five cards. A card's cost (in credits) comes from how far above his season he was and how much he
          played; "×" is his number against that season's league average for the role.
        </Box>
      )}

      {done && (
        <>
          <Box sx={{ textAlign: 'center', py: 1 }}>
            <Box sx={{ ...mono, fontSize: 44 }}>{`${made}/${results.length}`}</Box>
            <Box sx={{ fontSize: 15, color: colors.textMed }}>{`seasons your XI would have made the playoffs · topped ${results.filter((r) => r.topped).length}`}</Box>
          </Box>
          <Strip results={results} />
          <Box sx={{ fontSize: 13, color: colors.textMed }}>{`The best XI this deal allowed on the budget: ${best.filter((r) => r.made).length}/${best.length}. Swap a pick to try again.`}</Box>
          <Box sx={{ fontSize: 11.5, color: colors.textLo }}>
            How scoring works: each pick's numbers against his season's league average for the role. Your XI then plays each
            of the 19 seasons against that season's real sides, the stronger side more likely to win each game; top four on
            wins makes the playoffs. A game, not a prediction.
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Box component="button" type="button" onClick={() => navigate({ search: `?d=${newDeal()}` })}
              sx={{ all: 'unset', cursor: 'pointer', flex: 1, textAlign: 'center', py: 1.1, borderRadius: '12px', border: `1px solid ${colors.borderStrong}` }}>New deal</Box>
            <Box component="button" type="button" onClick={() => {
              const url = window.location.href;
              const text = `Season Draft: my XI makes the IPL playoffs in ${made}/${results.length} seasons. Same deal, can you beat it?`;
              if (navigator.share) navigator.share({ title: 'Season Draft', text, url }).catch(() => {}); else navigator.clipboard?.writeText(`${text} ${url}`);
            }} sx={{ all: 'unset', cursor: 'pointer', flex: 2, textAlign: 'center', py: 1.1, borderRadius: '12px', bgcolor: colors.accent, color: colors.bg, fontWeight: 600 }}>
              Share
            </Box>
          </Box>
        </>
      )}

      <Drawer anchor="bottom" open={open != null} onClose={() => setOpen(null)}
        PaperProps={{ sx: { bgcolor: colors.bg, color: colors.textHi, borderTopLeftRadius: 16, borderTopRightRadius: 16, maxHeight: '85vh' } }}>
        {open != null && (
          <Box sx={{ maxWidth: 560, mx: 'auto', width: '100%', boxSizing: 'border-box', p: 2, pb: 'calc(16px + env(safe-area-inset-bottom, 0px))', display: 'flex', flexDirection: 'column', gap: 1 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
              <Box sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 20 }}>{SLOTS[open].label}</Box>
              {picks[open] && (
                <Box component="button" type="button" onClick={() => setPick(open, null)} sx={{ all: 'unset', cursor: 'pointer', fontSize: 13, color: colors.textLo }}>Clear</Box>
              )}
            </Box>
            {dealt[open].map((c, n) => (
              <CardRow key={c.name} card={c} slot={SLOTS[open]} cost={costOf(c, open, table)}
                why={picks[open] === c ? 'picked' : why(c, open)} onPick={() => setPick(open, n)} />
            ))}
          </Box>
        )}
      </Drawer>
    </Box>
  );
};

export default SeasonDraftGame;
