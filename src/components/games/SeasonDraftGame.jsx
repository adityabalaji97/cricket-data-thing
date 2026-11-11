import React, { useEffect, useMemo, useState } from 'react';
import { Box, Drawer } from '@mui/material';
import { keyframes } from '@mui/system';
import StarRounded from '@mui/icons-material/StarRounded';
import { useLocation, useNavigate } from 'react-router-dom';
import config from '../../config';
import { colors, fonts } from '../../theme/hindsightDark';
import OverseasMark from '../common/OverseasMark';
import { BallIcon, BatIcon, GloveIcon } from '../common/CricketIcons';
import DATA_VERSION from '../../utils/draftDataVersion';
import {
  BUDGET, COST_MIN, OVERSEAS_MAX, ROLE_NAMES, SLOTS, bestFromDeal, checkPicks, costOf, costTable, deal, isBatSlot, profile,
  roleEdges, seasonResults,
} from '../../utils/draftEngine';

// 19-0, formerly Season Draft (XI_BUILDER_PLAN.md X10), at /games/19-0. Three stages, all in the URL (d = the deal,
// p = the picks, r = locked in):
//   draft     fill eleven slots in any order, five cards a slot, on a budget, four overseas at most, a wicketkeeper;
//             no score shown while drafting
//   simulate  after "Lock in": a short "playing 19 seasons" screen (skipped with reduced motion, or on a shared link)
//   result    one phone screen, made to be screenshotted and shared: the record, one line, why, the 19 seasons
//             (tap one for its finish), the XI, play again, the data credit. The URL unfurls as a card (share.mjs).
// The score is a record: seasons it made the playoffs v seasons it missed ("13-6"; 19-0 is the perfect run). The game's
// rule, not a prediction. Phone rules (13 Nov 2026 audit): one-line text at 390px, 11px+ text, 32px+ tap targets,
// nothing told by colour alone, help in a sheet rather than on the screen.

export const GAME_NAME = '19-0';
const mono = { fontFamily: fonts.mono, fontVariantNumeric: 'tabular-nums' };
const oneLine = { whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' };
const newDeal = () => Math.random().toString(36).slice(2, 10);
const BOWL_ROLES = ['pp_pace', 'mid_spin', 'death_pace'];
const f1 = (x) => (x == null || !Number.isFinite(x) ? '–' : x.toFixed(1));
const overs = (balls) => `${Math.floor(balls / 6)}${balls % 6 ? `.${balls % 6}` : ''}`;
const ordinal = (n) => `${n}${['th', 'st', 'nd', 'rd'][(n % 100 > 10 && n % 100 < 14) || n % 10 > 3 ? 0 : n % 10]}`;
const GOLD = '#c9a227';
const SIM_MS = 2600;
const CREDIT = 'Data: Himanish Ganjoo & TechRadar, Cricsheet';
const linkBtn = { all: 'unset', cursor: 'pointer', minHeight: 32, display: 'inline-flex', alignItems: 'center', fontSize: 13, color: colors.textMed,
  textDecoration: 'underline', textUnderlineOffset: 3, '&:focus-visible': { outline: `2px solid ${colors.accent}` } };

const Marks = ({ card, size = 14 }) => (
  <>
    {card.overseas && <OverseasMark size={size} />}
    {card.wk && <GloveIcon sx={{ fontSize: size + 1, ml: 0.5, flexShrink: 0, color: colors.textMed }} />}
  </>
);

// A card: the season's headline numbers, the way fans judge a season. Batting at the slot's positions, bowling over
// the whole season (a batter's too: it counts when he's among the XI's busiest bowlers). The era-adjusted ratios the
// score uses stay behind the scenes.
const batLines = (b) => [
  b.outs ? `Avg ${f1(b.runs / b.outs)} · SR ${f1((100 * b.runs) / b.balls)} · BpD ${f1(b.balls / b.outs)}` : `Never out · SR ${f1((100 * b.runs) / b.balls)}`,
  `${b.runs} runs · ${b.inns} inns`,
];
const bowlLines = (w) => [
  `Avg ${w.wkts ? f1(w.runs / w.wkts) : '–'} · SR ${w.wkts ? f1(w.balls / w.wkts) : '–'} · Econ ${((6 * w.runs) / w.balls).toFixed(2)}`,
  `${w.wkts} wkts · ${overs(w.balls)} ov`,
];

const Stat = ({ Icon, lines }) => (
  <Box sx={{ display: 'grid', gridTemplateColumns: '22px 1fr', columnGap: 0.75, mt: 0.5 }}>
    <Icon sx={{ fontSize: 16, color: colors.textLo, mt: '2px' }} />
    <Box sx={{ minWidth: 0 }}>
      <Box sx={{ ...mono, ...oneLine, fontSize: 13.5, color: colors.textHi }}>{lines[0]}</Box>
      <Box sx={{ fontSize: 12, color: colors.textMed }}>{lines[1]}</Box>
    </Box>
  </Box>
);

// A greyed card keeps its reason at full strength ("Four overseas already"): only the card's content fades.
const CardRow = ({ card, slotIndex, cost, onPick, why, picked }) => {
  const slot = SLOTS[slotIndex];
  const bat = isBatSlot(slotIndex) ? card.bat?.[slot.key] : null;
  const bowls = card.bowl && Object.keys(card.roles).some((r) => BOWL_ROLES.includes(r));
  const off = !!why;
  const fade = { opacity: off && !picked ? 0.4 : 1 };
  return (
    <Box component="button" type="button" disabled={off} onClick={onPick}
      sx={{ all: 'unset', boxSizing: 'border-box', cursor: off ? 'default' : 'pointer', display: 'block', bgcolor: colors.surface1,
        border: `1px solid ${picked ? colors.accent : colors.border}`, borderRadius: '14px', px: 1.5, py: 1.1,
        '&:hover': { borderColor: off ? undefined : colors.accent }, '&:focus-visible': { outline: `2px solid ${colors.accent}`, outlineOffset: 2 } }}>
      <Box sx={fade}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', minWidth: 0 }}>
            <Box sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 18, minWidth: 0, ...oneLine }}>{`${card.name} ${card.season}`}</Box>
            <Marks card={card} size={16} />
          </Box>
          <Box sx={{ ...mono, fontSize: 14, color: colors.accent, whiteSpace: 'nowrap' }}>{`${cost} credits`}</Box>
        </Box>
        <Box sx={{ fontSize: 11.5, color: colors.textLo }}>{card.team}</Box>
      </Box>
      {why && <Box sx={{ fontSize: 12, fontWeight: 600, color: picked ? colors.accent : colors.textMed, mt: 0.25 }}>{why}</Box>}
      <Box sx={fade}>
        {bat && <Stat Icon={BatIcon} lines={batLines(bat)} />}
        {bowls && <Stat Icon={BallIcon} lines={bowlLines(card.bowl)} />}
      </Box>
    </Box>
  );
};

const Sheet = ({ open, onClose, children }) => (
  <Drawer anchor="bottom" open={open} onClose={onClose}
    PaperProps={{ sx: { bgcolor: colors.bg, color: colors.textHi, borderTopLeftRadius: 16, borderTopRightRadius: 16, maxHeight: '85vh' } }}>
    <Box sx={{ maxWidth: 560, mx: 'auto', width: '100%', boxSizing: 'border-box', p: 2, pb: 'calc(16px + env(safe-area-inset-bottom, 0px))',
      display: 'flex', flexDirection: 'column', gap: 1 }}>
      {children}
    </Box>
  </Drawer>
);

const HOW = [
  `Fill eleven slots, in any order, from five cards each: IPL player-seasons from 2008 to 2026. You have ${BUDGET} credits, up to four overseas players and at least one wicketkeeper.`,
  "Batting numbers are at that slot's positions; bowling is the whole season. A batter who bowls also joins your attack when he's among its two busiest bowlers in a phase. Bowlers bat 8-11, which isn't scored.",
  "A card's cost comes from how good that season was for its time, discounted for small samples.",
  "Lock in, and your XI plays every IPL season against that year's real sides: each pick measured against his own season, so eras compare, and each game more likely to go to the stronger side. Top four makes the playoffs; 19-0 is the perfect run.",
  'A game, not a prediction.',
];
const HowItWorks = ({ open, onClose }) => (
  <Sheet open={open} onClose={onClose}>
    <Box sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 20 }}>How 19-0 works</Box>
    {HOW.map((t) => <Box key={t.slice(0, 24)} sx={{ fontSize: 14, color: colors.textMed, lineHeight: 1.5 }}>{t}</Box>)}
  </Sheet>
);

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

const Result = ({ picks, table, results, best, edges, onReplay, onSameDeal, onHow }) => {
  const [sel, setSel] = useState(null);
  const made = results.filter((r) => r.made).length;
  const topped = results.filter((r) => r.topped).length;
  const bestMade = best.filter((r) => r.made).length;
  const line = made === 0 ? 'Missed the playoffs in all 19 seasons'
    : `Playoffs in ${made} of 19${topped ? ` · topped the table ${topped === 1 ? 'once' : `${topped} times`}` : ''}`;
  const share = () => {
    const url = window.location.href;
    const text = `${GAME_NAME}: my IPL XI went ${made}-${19 - made}. Same deal, can you beat it?`;
    if (navigator.share) navigator.share({ title: GAME_NAME, text, url }).catch(() => {}); else navigator.clipboard?.writeText(`${text} ${url}`);
  };
  const s = sel != null ? results[sel] : null;
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.85 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <Box sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 20 }}>{GAME_NAME}</Box>
        <Box sx={{ fontSize: 11.5, color: colors.textLo }}>hindsightcricket.com</Box>
      </Box>
      <Box>
        <Box sx={{ ...mono, fontSize: 58, lineHeight: 1, color: colors.accent }}>{`${made}-${19 - made}`}</Box>
        <Box sx={{ fontSize: 14.5, color: colors.textHi, mt: 0.75, ...oneLine }}>{line}</Box>
        <Box sx={{ fontSize: 13, color: colors.textMed, mt: 0.25, ...oneLine }}>
          {`Strongest: ${ROLE_NAMES[edges.strongest]} · Weakest: ${ROLE_NAMES[edges.weakest]}`}
        </Box>
      </Box>
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(10, 1fr)', gap: '3px' }}>
        {results.map((r, n) => (
          <Box key={r.season} component="button" type="button" onClick={() => setSel(n === sel ? null : n)}
            aria-label={`${r.season}: finished ${ordinal(r.rank)} of ${r.of}`}
            sx={{ all: 'unset', boxSizing: 'border-box', cursor: 'pointer', ...mono, fontSize: 11.5, height: 32, display: 'flex', alignItems: 'center',
              justifyContent: 'center', gap: '1px', borderRadius: '6px', outline: n === sel ? `2px solid ${colors.textHi}` : 'none', outlineOffset: 1,
              bgcolor: r.topped ? GOLD : r.made ? colors.accent : colors.surface2, color: r.made ? colors.bg : colors.textLo }}>
            {r.season.slice(-2)}{r.topped && <StarRounded sx={{ fontSize: 11 }} />}
          </Box>
        ))}
      </Box>
      <Box sx={{ fontSize: 12.5, color: s ? colors.textHi : colors.textLo, ...oneLine }}>
        {s ? `IPL ${s.season}: finished ${ordinal(s.rank)} of ${s.of}, won ${s.wins} of ${s.games}` : 'Tap a season for where your XI finished'}
      </Box>
      <Box sx={{ display: 'flex', gap: 1.5, fontSize: 11, color: colors.textLo }}>
        {[[colors.accent, 'playoffs', false], [GOLD, 'top of the table', true], [colors.surface2, 'missed', false]].map(([c, l, star]) => (
          <Box key={l} sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Box sx={{ width: 11, height: 11, borderRadius: '2px', bgcolor: c, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              {star && <StarRounded sx={{ fontSize: 9, color: colors.bg }} />}
            </Box>{l}
          </Box>
        ))}
      </Box>
      <Box sx={{ bgcolor: colors.surface1, border: `1px solid ${colors.border}`, borderRadius: '12px', px: 1.25, py: 0.6 }}>
        {picks.map((c, i) => (
          <Box key={c.name} sx={{ display: 'grid', gridTemplateColumns: '58px 1fr auto', alignItems: 'center', gap: 1, py: '2px' }}>
            <Box sx={{ fontSize: 11, color: colors.textLo, whiteSpace: 'nowrap' }}>{SLOTS[i].label}</Box>
            <Box sx={{ display: 'flex', alignItems: 'center', minWidth: 0 }}>
              <Box sx={{ fontSize: 13.5, ...oneLine }}>{`${c.name} ${c.season}`}</Box>
              <Marks card={c} size={13} />
            </Box>
            <Box sx={{ ...mono, fontSize: 12, color: colors.textMed }}>{costOf(c, i, table)}</Box>
          </Box>
        ))}
      </Box>
      <Box sx={{ fontSize: 12.5, color: colors.textMed, ...oneLine }}>
        {bestMade > made ? `The best XI this deal allowed went ${bestMade}-${19 - bestMade}.` : 'No XI from this deal does better.'}
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
      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
        <Box component="button" type="button" onClick={onSameDeal} sx={linkBtn}>Try this same deal</Box>
        <Box component="button" type="button" onClick={onHow} sx={linkBtn}>How it works</Box>
      </Box>
      <Box sx={{ fontSize: 11, color: colors.textLo, ...oneLine }}>{CREDIT}</Box>
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
  const [how, setHow] = useState(false);
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
  const edges = useMemo(() => (showResult ? roleEdges(profile(picks), data.seasons, data.roles) : null), [showResult, picks, data]);
  const best = useMemo(() => (showResult ? seasonResults(profile(bestFromDeal(dealt, data.roles, table)), data.seasons, data.roles, d) : null),
    [showResult, dealt, data, d, table]);

  if (error) return <Box sx={{ p: 2, color: colors.textLo }}>The draft couldn't load just now. Try again shortly.</Box>;
  if (!dealt) return <Box sx={{ p: 2, color: colors.textLo }}>Dealing…</Box>;
  const wrap = (child) => (
    <Box sx={{ maxWidth: 560, mx: 'auto', px: 2, pt: 1.5, pb: 4, color: colors.textHi, display: 'flex', flexDirection: 'column', gap: 1.5 }}>
      {child}
      <HowItWorks open={how} onClose={() => setHow(false)} />
    </Box>
  );
  if (showResult && simulating) return wrap(<Simulating seasons={data.seasons} />);
  if (showResult) {
    return wrap(<Result picks={picks} table={table} results={results} best={best} edges={edges} onHow={() => setHow(true)}
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
    if (others.some((c) => c && c.name === card.name)) return 'Already in your XI';
    const st = checkPicks(others, table);
    if (card.overseas && st.overseas >= OVERSEAS_MAX) return 'Four overseas already';
    const empty = others.filter((c, i) => !c && i !== slot).length;
    if (costOf(card, slot, table) > st.left - COST_MIN * empty) return 'Over the budget';
    return null;
  };
  const lockReason = filled < SLOTS.length ? `Pick ${SLOTS.length - filled} more` : !state.keeper ? 'Your XI needs a wicketkeeper' : null;
  const keeperNote = (
    <Box component="span" sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.25, color: state.keeper ? colors.accent : colors.textMed }}>
      <GloveIcon sx={{ fontSize: 12 }} />{state.keeper ? '✓' : 'needed'}
    </Box>
  );
  const chip = { display: 'inline-flex', alignItems: 'center', gap: 0.5, fontSize: 12, color: colors.textMed, border: `1px solid ${colors.border}`,
    borderRadius: '999px', px: 1, height: 28, boxSizing: 'border-box' };

  return wrap(
    <>
      <Box>
        <Box sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 26 }}>{GAME_NAME}</Box>
        <Box sx={{ color: colors.textMed, fontSize: 13.5, ...oneLine }}>Draft an IPL XI from 19 seasons. Can it go 19-0?</Box>
        <Box sx={{ display: 'flex', gap: 0.75, mt: 1, flexWrap: 'wrap', alignItems: 'center' }}>
          <Box sx={chip}>{`${BUDGET} credits`}</Box>
          <Box sx={chip}><OverseasMark size={12} sx={{ ml: 0 }} />4 max</Box>
          <Box sx={chip}><GloveIcon sx={{ fontSize: 13 }} />1 keeper</Box>
          <Box component="button" type="button" onClick={() => setHow(true)}
            sx={{ all: 'unset', ...chip, height: 32, cursor: 'pointer', color: colors.accent, '&:focus-visible': { outline: `2px solid ${colors.accent}` } }}>How it works</Box>
        </Box>
      </Box>

      <Box sx={{ display: 'flex', gap: 1 }}>
        {[
          [`${state.left}`, <>credits left</>],
          [`${state.overseas}/${OVERSEAS_MAX}`, <><OverseasMark size={11} sx={{ ml: 0, mr: 0.4, color: colors.textLo, verticalAlign: '-1px' }} />overseas</>],
          [`${filled}/11`, <>picked</>, keeperNote],
        ].map(([v, l, extra], n) => (
          <Box key={n} sx={{ flex: 1, minWidth: 0, bgcolor: colors.surface1, border: `1px solid ${colors.border}`, borderRadius: '12px', px: 1.25, py: 0.9 }}>
            <Box sx={{ ...mono, fontSize: 19 }}>{v}</Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 0.5, fontSize: 11, color: colors.textLo, whiteSpace: 'nowrap' }}>
              <span>{l}</span>{extra}
            </Box>
          </Box>
        ))}
      </Box>

      <Box sx={{ bgcolor: colors.surface1, border: `1px solid ${colors.border}`, borderRadius: '14px', px: 1.25, py: 0.5 }}>
        {SLOTS.map((slot, i) => {
          const c = picks[i];
          return (
            <Box key={i} component="button" type="button" onClick={() => setOpen(i)}
              sx={{ all: 'unset', cursor: 'pointer', boxSizing: 'border-box', display: 'grid', gridTemplateColumns: '64px 1fr auto', alignItems: 'center', gap: 1,
                minHeight: 40, width: '100%', borderTop: i ? `1px solid ${colors.border}` : 'none', '&:focus-visible': { outline: `2px solid ${colors.accent}` } }}>
              <Box sx={{ fontSize: 12, color: colors.textLo, whiteSpace: 'nowrap' }}>{slot.label}</Box>
              <Box sx={{ display: 'flex', alignItems: 'center', minWidth: 0 }}>
                <Box sx={{ fontSize: 14.5, minWidth: 0, ...oneLine, color: c ? colors.textHi : colors.accent }}>{c ? `${c.name} ${c.season}` : 'Pick'}</Box>
                {c && <Marks card={c} />}
              </Box>
              <Box sx={{ ...mono, fontSize: 13, color: colors.textMed }}>{c ? `${costOf(c, i, table)}` : ''}</Box>
            </Box>
          );
        })}
      </Box>

      <Box component="button" type="button" disabled={!!lockReason} onClick={lockIn}
        sx={{ all: 'unset', boxSizing: 'border-box', cursor: lockReason ? 'default' : 'pointer', textAlign: 'center', py: 1.3, borderRadius: '12px', fontWeight: 600,
          bgcolor: lockReason ? colors.surface2 : colors.accent, color: lockReason ? colors.textMed : colors.bg }}>
        {lockReason || 'Lock in XI'}
      </Box>

      <Sheet open={open != null} onClose={() => setOpen(null)}>
        {open != null && (
          <>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Box sx={{ minWidth: 0 }}>
                <Box sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 20 }}>{SLOTS[open].label}</Box>
                <Box sx={{ fontSize: 12, color: colors.textMed, display: 'flex', alignItems: 'center', gap: 0.75, whiteSpace: 'nowrap' }}>
                  {`${state.left} credits left ·`}
                  <Box component="span" sx={{ display: 'inline-flex', alignItems: 'center' }}><OverseasMark size={12} sx={{ ml: 0, mr: 0.3 }} />{`${state.overseas}/${OVERSEAS_MAX}`}</Box>·
                  {keeperNote}
                </Box>
              </Box>
              {picks[open] && (
                <Box component="button" type="button" onClick={() => setPick(open, null)}
                  sx={{ all: 'unset', cursor: 'pointer', minHeight: 32, minWidth: 48, display: 'inline-flex', alignItems: 'center', justifyContent: 'flex-end',
                    fontSize: 13.5, color: colors.textMed }}>Clear</Box>
              )}
            </Box>
            {dealt[open].map((c, n) => (
              <CardRow key={c.name} card={c} slotIndex={open} cost={costOf(c, open, table)} picked={picks[open] === c}
                why={picks[open] === c ? 'In your XI' : why(c, open)} onPick={() => setPick(open, n)} />
            ))}
          </>
        )}
      </Sheet>
    </>,
  );
};

export default SeasonDraftGame;
