import React, { useEffect, useMemo, useState } from 'react';
import { Box, Drawer } from '@mui/material';
import { keyframes } from '@mui/system';
import { useLocation, useNavigate } from 'react-router-dom';
import config from '../../config';
import { colors, fonts } from '../../theme/hindsightDark';
import OverseasMark from '../common/OverseasMark';
import DATA_VERSION from '../../utils/draftDataVersion';
import {
  BUDGET, COST_MIN, OVERSEAS_MAX, SLOTS, bestFromDeal, checkPicks, costOf, costTable, deal, isBatSlot, profile, seasonResults,
} from '../../utils/draftEngine';

// 19-0, formerly Season Draft (XI_BUILDER_PLAN.md X10), at /games/19-0. Three stages, all in the URL (d = the deal, p = the picks, r = locked in):
//   draft     fill eleven slots in any order, five cards a slot, on a budget, four overseas at most, a wicketkeeper;
//             no score shown while drafting
//   simulate  after "Lock in": a short "playing 19 seasons" screen (skipped with reduced motion, or on a shared link)
//   result    one screen, made to be screenshotted and shared: the score, a one-line summary, the 19 seasons, the XI,
//             play again. The same URL unfurls as a card (api/_lib/share.mjs draftSummary).
// The score is a record: seasons it made the playoffs v seasons it missed ("13-6"; 19-0 is the perfect run). The game's
// rule, not a prediction.

export const GAME_NAME = '19-0';  // 13 Nov 2026: the score is a record, playoffs reached v missed (13-6)
const mono = { fontFamily: fonts.mono, fontVariantNumeric: 'tabular-nums' };
const newDeal = () => Math.random().toString(36).slice(2, 10);
const BOWL_ROLES = ['pp_pace', 'mid_spin', 'death_pace'];
const f1 = (x) => (x == null || !Number.isFinite(x) ? '–' : x.toFixed(1));
const overs = (balls) => `${Math.floor(balls / 6)}${balls % 6 ? `.${balls % 6}` : ''}`;
const SIM_MS = 2600;

const WkMark = () => (
  <Box component="span" role="img" aria-label="wicketkeeper" title="Wicketkeeper"
    sx={{ ml: 0.5, flexShrink: 0, px: '4px', py: '1px', borderRadius: '4px', border: `1px solid ${colors.borderStrong}`,
      fontFamily: fonts.mono, fontSize: 9.5, lineHeight: 1.2, letterSpacing: '0.04em', color: colors.textMed }}>WK</Box>
);
const Marks = ({ card, size }) => (
  <>
    {card.overseas && <OverseasMark size={size} />}
    {card.wk && <WkMark />}
  </>
);

// A card: the season's headline numbers, the way fans judge a season. Batting at the slot's positions, bowling over
// the whole season (a batter's too: it counts when he's among the XI's busiest bowlers). The era-adjusted ratios the
// score uses stay behind the scenes.
const batLines = (b) => [
  `Avg ${b.outs ? f1(b.runs / b.outs) : '–'} · SR ${f1((100 * b.runs) / b.balls)} · BpD ${b.outs ? f1(b.balls / b.outs) : '–'}`,
  `${b.runs} runs · ${b.inns} inns`,
];
const bowlLines = (w) => [
  `Avg ${w.wkts ? f1(w.runs / w.wkts) : '–'} · SR ${w.wkts ? f1(w.balls / w.wkts) : '–'} · Econ ${((6 * w.runs) / w.balls).toFixed(2)}`,
  `${w.wkts} wkts · ${overs(w.balls)} ov`,
];

const Stat = ({ label, lines }) => (
  <Box sx={{ display: 'grid', gridTemplateColumns: '38px 1fr', columnGap: 1, mt: 0.5 }}>
    <Box sx={{ fontSize: 10.5, letterSpacing: '0.06em', textTransform: 'uppercase', color: colors.textLo, pt: '3px' }}>{label}</Box>
    <Box>
      <Box sx={{ ...mono, fontSize: 13.5, color: colors.textHi }}>{lines[0]}</Box>
      <Box sx={{ fontSize: 12, color: colors.textMed }}>{lines[1]}</Box>
    </Box>
  </Box>
);

const CardRow = ({ card, slotIndex, cost, onPick, why }) => {
  const slot = SLOTS[slotIndex];
  const bat = isBatSlot(slotIndex) ? card.bat?.[slot.key] : null;
  const bowls = card.bowl && Object.keys(card.roles).some((r) => BOWL_ROLES.includes(r));
  return (
    <Box component="button" type="button" disabled={!!why} onClick={onPick}
      sx={{ all: 'unset', boxSizing: 'border-box', cursor: why ? 'default' : 'pointer', opacity: why ? 0.45 : 1, display: 'block', bgcolor: colors.surface1,
        border: `1px solid ${colors.border}`, borderRadius: '14px', px: 1.5, py: 1.1, '&:hover': { borderColor: why ? colors.border : colors.accent },
        '&:focus-visible': { outline: `2px solid ${colors.accent}`, outlineOffset: 2 } }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', minWidth: 0 }}>
          <Box sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 18, minWidth: 0, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {`${card.name} ${card.season}`}
          </Box>
          <Marks card={card} size={16} />
        </Box>
        <Box sx={{ ...mono, fontSize: 15, color: colors.accent, whiteSpace: 'nowrap' }}>{`${cost} cr`}</Box>
      </Box>
      <Box sx={{ fontSize: 11.5, color: colors.textLo }}>{[card.team, why].filter(Boolean).join(' · ')}</Box>
      {bat && <Stat label="Bat" lines={batLines(bat)} />}
      {bowls && <Stat label="Bowl" lines={bowlLines(card.bowl)} />}
    </Box>
  );
};

const pulse = keyframes`0% { background-color: ${colors.surface2}; } 30% { background-color: ${colors.accent}; } 100% { background-color: ${colors.surface2}; }`;

// The pretend calculation: the 19 seasons light up in turn while the counter runs through the years.
const Simulating = ({ seasons }) => {
  const [i, setI] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setI((x) => Math.min(x + 1, seasons.length - 1)), SIM_MS / seasons.length);
    return () => clearInterval(t);
  }, [seasons.length]);
  return (
    <Box sx={{ minHeight: 420, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', gap: 2, textAlign: 'center' }}>
      <Box sx={{ fontSize: 13, color: colors.textLo, letterSpacing: '0.08em', textTransform: 'uppercase' }}>Playing your XI through</Box>
      <Box sx={{ ...mono, fontSize: 48 }}>{`IPL ${seasons[i].season}`}</Box>
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(10, 22px)', gap: '6px' }}>
        {seasons.map((s, n) => (
          <Box key={s.season} sx={{ width: 22, height: 22, borderRadius: '5px', bgcolor: colors.surface2,
            animation: `${pulse} ${SIM_MS / 4}ms ease-out ${(n * SIM_MS) / seasons.length}ms 1 both` }} />
        ))}
      </Box>
      <Box sx={{ fontSize: 12.5, color: colors.textLo }}>against each season's real sides</Box>
    </Box>
  );
};

const Result = ({ picks, table, results, best, onReplay, onSameDeal }) => {
  const made = results.filter((r) => r.made).length;
  const topped = results.filter((r) => r.topped).length;
  const bestMade = best.filter((r) => r.made).length;
  const summary = made === 0 ? 'Missed the playoffs in every one of the 19 IPL seasons.'
    : `Made the playoffs in ${made} of 19 IPL seasons${topped ? `, and topped the table in ${topped}` : ''}.`;
  const share = () => {
    const url = window.location.href;
    const text = `${GAME_NAME}: my XI went ${made}-${19 - made}, the IPL playoffs in ${made} of 19 seasons. Same deal, can you beat it?`;
    if (navigator.share) navigator.share({ title: GAME_NAME, text, url }).catch(() => {}); else navigator.clipboard?.writeText(`${text} ${url}`);
  };
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.25 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <Box sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 20 }}>{GAME_NAME}</Box>
        <Box sx={{ fontSize: 11.5, color: colors.textLo }}>hindsightcricket.com</Box>
      </Box>
      <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1.25 }}>
        <Box sx={{ ...mono, fontSize: 56, lineHeight: 1, color: colors.accent, whiteSpace: 'nowrap' }}>{`${made}-${19 - made}`}</Box>
        <Box sx={{ fontSize: 15, color: colors.textHi, lineHeight: 1.3 }}>{summary}</Box>
      </Box>
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(10, 1fr)', gap: '4px' }}>
        {results.map((r) => (
          <Box key={r.season} title={`${r.season}: finished ${r.rank} of ${r.of}, won ${r.wins} of ${r.games}`}
            sx={{ ...mono, fontSize: 11.5, textAlign: 'center', py: '5px', borderRadius: '6px',
              bgcolor: r.topped ? '#c9a227' : r.made ? colors.accent : colors.surface2, color: r.made ? colors.bg : colors.textLo }}>
            {r.season.slice(-2)}
          </Box>
        ))}
      </Box>
      <Box sx={{ display: 'flex', gap: 1.5, fontSize: 11, color: colors.textLo }}>
        {[[colors.accent, 'playoffs'], ['#c9a227', 'top of the table'], [colors.surface2, 'missed']].map(([c, l]) => (
          <Box key={l} sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}><Box sx={{ width: 9, height: 9, borderRadius: '2px', bgcolor: c }} />{l}</Box>
        ))}
      </Box>
      <Box sx={{ bgcolor: colors.surface1, border: `1px solid ${colors.border}`, borderRadius: '12px', px: 1.25, py: 0.75 }}>
        {picks.map((c, i) => (
          <Box key={c.name} sx={{ display: 'grid', gridTemplateColumns: '64px 1fr auto', alignItems: 'center', gap: 1, py: '3px' }}>
            <Box sx={{ fontSize: 11, color: colors.textLo, whiteSpace: 'nowrap' }}>{SLOTS[i].label.replace('Number ', 'No. ').replace(' bowler', '')}</Box>
            <Box sx={{ display: 'flex', alignItems: 'center', minWidth: 0 }}>
              <Box sx={{ fontSize: 13.5, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{`${c.name} ${c.season}`}</Box>
              <Marks card={c} size={13} />
            </Box>
            <Box sx={{ ...mono, fontSize: 12, color: colors.textMed }}>{costOf(c, i, table)}</Box>
          </Box>
        ))}
      </Box>
      <Box sx={{ fontSize: 12.5, color: colors.textMed }}>
        {bestMade > made ? `The best XI this deal allowed made ${bestMade}.` : 'No XI from this deal does better.'}
      </Box>
      <Box sx={{ display: 'flex', gap: 1 }}>
        <Box component="button" type="button" onClick={onReplay}
          sx={{ all: 'unset', cursor: 'pointer', flex: 2, textAlign: 'center', py: 1.1, borderRadius: '12px', bgcolor: colors.accent, color: colors.bg, fontWeight: 600 }}>
          Play again
        </Box>
        <Box component="button" type="button" onClick={share}
          sx={{ all: 'unset', cursor: 'pointer', flex: 1, textAlign: 'center', py: 1.1, borderRadius: '12px', border: `1px solid ${colors.borderStrong}` }}>
          Share
        </Box>
      </Box>
      <Box component="button" type="button" onClick={onSameDeal}
        sx={{ all: 'unset', cursor: 'pointer', alignSelf: 'center', fontSize: 13, color: colors.textMed, textDecoration: 'underline', textUnderlineOffset: 3 }}>
        Try this same deal yourself
      </Box>
      <Box sx={{ fontSize: 10.5, color: colors.textLo }}>
        Each pick's numbers are measured against his own season, so eras compare; the XI then plays each season against
        that year's real sides. A game, not a prediction.
      </Box>
    </Box>
  );
};

const SeasonDraftGame = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const q = new URLSearchParams(location.search);
  const d = q.get('d');
  const locked = q.get('r') === '1';
  const pStr = (q.get('p') || '').padEnd(SLOTS.length, '-').slice(0, SLOTS.length);
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);
  const [open, setOpen] = useState(null);  // the slot whose cards are showing
  const [simulating, setSimulating] = useState(false);
  useEffect(() => {
    document.title = `${GAME_NAME} · Hindsight`;
    fetch(`${config.API_URL}/games/season-draft/data?v=${DATA_VERSION}`).then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then(setData).catch(() => setError(true));
  }, []);
  // A new draft gets its own deal, written into the URL so the draft is a link.
  useEffect(() => { if (!d) navigate({ search: `?d=${newDeal()}` }, { replace: true }); }, [d, navigate]);
  useEffect(() => {
    if (!simulating) return undefined;
    const t = setTimeout(() => setSimulating(false), SIM_MS + 300);
    return () => clearTimeout(t);
  }, [simulating]);
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
  const state = table && dealt ? checkPicks(picks, table) : null;
  const showResult = locked && !!state?.complete;
  const results = useMemo(() => (showResult ? seasonResults(profile(picks), data.seasons, data.roles, d) : null), [showResult, picks, data, d]);
  const best = useMemo(() => (showResult ? seasonResults(profile(bestFromDeal(dealt, data.roles, table)), data.seasons, data.roles, d) : null),
    [showResult, dealt, data, d, table]);

  if (error) return <Box sx={{ p: 2, color: colors.textLo }}>The draft couldn't load just now. Try again shortly.</Box>;
  if (!dealt) return <Box sx={{ p: 2, color: colors.textLo }}>Dealing…</Box>;
  const wrap = (child) => (
    <Box sx={{ maxWidth: 560, mx: 'auto', px: 2, pt: 1.5, pb: 4, color: colors.textHi, display: 'flex', flexDirection: 'column', gap: 1.5 }}>{child}</Box>
  );
  if (showResult && simulating) return wrap(<Simulating seasons={data.seasons} />);
  if (showResult) {
    return wrap(<Result picks={picks} table={table} results={results} best={best}
      onReplay={() => navigate({ search: `?d=${newDeal()}` })} onSameDeal={() => navigate({ search: `?d=${d}` })} />);
  }

  const filled = picks.filter(Boolean).length;
  const setPick = (slot, idx) => {
    const chars = pStr.split(''); chars[slot] = idx == null ? '-' : String(idx);
    navigate({ search: `?d=${d}&p=${chars.join('')}` }, { replace: true });
    setOpen(null);
  };
  const lockIn = () => {
    const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    setSimulating(!reduced);
    navigate({ search: `?d=${d}&p=${pStr}&r=1` });
    window.scrollTo(0, 0);
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
  const lockReason = filled < SLOTS.length ? `Pick ${SLOTS.length - filled} more`
    : !state.keeper ? 'Your XI needs a wicketkeeper (WK)' : null;

  return wrap(
    <>
      <Box>
        <Box sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 26 }}>{GAME_NAME}</Box>
        <Box sx={{ color: colors.textMed, fontSize: 13.5 }}>
          {`Build an XI from 19 years of IPL seasons: ${BUDGET} credits, up to four overseas, a wicketkeeper. It plays all 19 seasons: playoffs reached v missed. Can it go 19-0?`}
        </Box>
      </Box>

      <Box sx={{ display: 'flex', gap: 1 }}>
        {[[`${state.left}`, `of ${BUDGET} credits left`], [`${state.overseas}/${OVERSEAS_MAX}`, 'overseas'], [`${filled}/11`, 'picked']].map(([v, l]) => (
          <Box key={l} sx={{ flex: 1, bgcolor: colors.surface1, border: `1px solid ${colors.border}`, borderRadius: '12px', px: 1.25, py: 0.9 }}>
            <Box sx={{ ...mono, fontSize: 19 }}>{v}</Box>
            <Box sx={{ fontSize: 11, color: colors.textLo }}>
              {l === 'overseas' && <OverseasMark size={11} sx={{ ml: 0, mr: 0.4, color: colors.textLo, verticalAlign: '-1px' }} />}{l}
            </Box>
          </Box>
        ))}
      </Box>

      <Box sx={{ bgcolor: colors.surface1, border: `1px solid ${colors.border}`, borderRadius: '14px', px: 1.25, py: 0.5 }}>
        {SLOTS.map((slot, i) => {
          const c = picks[i];
          return (
            <Box key={i} component="button" type="button" onClick={() => setOpen(i)}
              sx={{ all: 'unset', cursor: 'pointer', boxSizing: 'border-box', display: 'grid', gridTemplateColumns: '84px 1fr auto', alignItems: 'center', gap: 1,
                py: 0.9, width: '100%', borderTop: i ? `1px solid ${colors.border}` : 'none', '&:focus-visible': { outline: `2px solid ${colors.accent}` } }}>
              <Box sx={{ fontSize: 12, color: colors.textLo, whiteSpace: 'nowrap' }}>{slot.label}</Box>
              <Box sx={{ display: 'flex', alignItems: 'center', minWidth: 0 }}>
                <Box sx={{ fontSize: 14.5, minWidth: 0, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', color: c ? colors.textHi : colors.accent }}>
                  {c ? `${c.name} ${c.season}` : 'Pick'}
                </Box>
                {c && <Marks card={c} />}
              </Box>
              <Box sx={{ ...mono, fontSize: 13, color: colors.textMed }}>{c ? `${costOf(c, i, table)}` : ''}</Box>
            </Box>
          );
        })}
      </Box>

      <Box component="button" type="button" disabled={!!lockReason} onClick={lockIn}
        sx={{ all: 'unset', boxSizing: 'border-box', cursor: lockReason ? 'default' : 'pointer', textAlign: 'center', py: 1.3, borderRadius: '12px', fontWeight: 600,
          bgcolor: lockReason ? colors.surface2 : colors.accent, color: lockReason ? colors.textLo : colors.bg }}>
        {lockReason || 'Lock in XI'}
      </Box>
      <Box sx={{ fontSize: 11.5, color: colors.textLo }}>
        Tap any slot to see its five cards. Batters' numbers are at that slot's positions; bowling is the whole season. A
        batter who bowls also joins your attack when he's among its busiest bowlers. A card's cost (in credits) comes from
        how good that season was for its time.
      </Box>

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
              <CardRow key={c.name} card={c} slotIndex={open} cost={costOf(c, open, table)}
                why={picks[open] === c ? 'picked' : why(c, open)} onPick={() => setPick(open, n)} />
            ))}
          </Box>
        )}
      </Drawer>
    </>,
  );
};

export default SeasonDraftGame;
