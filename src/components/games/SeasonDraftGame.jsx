import React, { useEffect, useMemo, useState } from 'react';
import { Box } from '@mui/material';
import { useLocation, useNavigate } from 'react-router-dom';
import config from '../../config';
import { colors, fonts } from '../../theme/hindsightDark';
import { OVERSEAS_MAX, SLOTS, bestFromDeal, deal, profile, seasonResults } from '../../utils/draftEngine';

// Season Draft (XI_BUILDER_PLAN.md X10): eleven picks, three IPL player-seasons dealt per slot (the same for everyone
// today), then the XI against all 19 IPL seasons, era-adjusted. "Made the playoffs in N of 19" is the game's rule: in
// each season the XI's role profile ranks top four among that season's real sides (not a prediction).

const mono = { fontFamily: fonts.mono, fontVariantNumeric: 'tabular-nums' };
const UNIT = { openers: 'avg', top: 'SR', finishers: 'SR', pp_pace: 'wkts / 4 ov', mid_spin: 'wkts / 4 ov', death_pace: 'an over' };
const LABEL = { openers: 'opening', top: 'at 3-4', finishers: 'at 5-7', pp_pace: 'powerplay', mid_spin: 'middle overs', death_pace: 'death' };
const today = () => new Date(Date.now() + 5.5 * 3600e3).toISOString().slice(0, 10);  // the day in India

const fmtV = (k, v) => (k === 'openers' ? v.toFixed(1) : k === 'top' || k === 'finishers' ? v.toFixed(0) : v.toFixed(2));

const Card = ({ card, slot, onPick, disabled }) => (
  <Box component="button" type="button" disabled={disabled} onClick={onPick}
    sx={{ all: 'unset', cursor: disabled ? 'default' : 'pointer', opacity: disabled ? 0.45 : 1, display: 'block', bgcolor: colors.surface1,
      border: `1px solid ${colors.border}`, borderRadius: '14px', px: 1.75, py: 1.25, '&:hover': { borderColor: disabled ? colors.border : colors.accent } }}>
    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 1 }}>
      <Box sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 19 }}>{`${card.name} ${card.season}`}</Box>
      <Box sx={{ fontSize: 11.5, color: colors.textLo, whiteSpace: 'nowrap' }}>{[card.team, card.overseas ? 'overseas' : null].filter(Boolean).join(' · ')}</Box>
    </Box>
    {slot.roles.filter((r) => card.roles[r]).map((r) => {
      const x = card.roles[r];
      return (
        <Box key={r} sx={{ display: 'flex', justifyContent: 'space-between', mt: 0.4, fontSize: 13.5 }}>
          <Box sx={{ color: colors.textMed }}>{`${fmtV(r, x.v)} ${UNIT[r]} ${LABEL[r]} · ${x.balls} balls`}</Box>
          <Box sx={{ ...mono, color: (r === 'death_pace' ? x.r < 1 : x.r > 1) ? colors.accent : colors.textLo }}>{`${x.r.toFixed(2)}× the season`}</Box>
        </Box>
      );
    })}
  </Box>
);

const Strip = ({ results }) => (
  <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(52px, 1fr))', gap: 0.75 }}>
    {results.map((r) => (
      <Box key={r.season} title={`${r.season}: ${r.rank} of ${r.of}`}
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
  const day = q.get('d') || today();
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    document.title = 'Season Draft · Hindsight';
    fetch(`${config.API_URL}/games/season-draft/data`).then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then(setData).catch(() => setError(true));
  }, []);
  const dealt = useMemo(() => (data ? deal(data.cards, `season-draft-${day}`) : null), [data, day]);
  // Picks live in the URL (an index 0-2 per slot), so a finished draft is a link.
  const pStr = q.get('p') || '';
  const picks = pStr.split('').map(Number).filter((n) => n >= 0 && n <= 2);
  const chosen = useMemo(() => (dealt ? pStr.split('').map(Number).map((n, i) => dealt[i]?.[n]).filter(Boolean) : []), [dealt, pStr]);
  const pick = (n) => {
    const p = new URLSearchParams(location.search);
    p.set('p', [...picks, n].join('')); if (!q.get('d')) p.set('d', day);
    navigate({ search: `?${p.toString()}` }, { replace: true });
  };
  const restart = () => navigate({ search: `?d=${day}` }, { replace: true });
  const done = dealt && chosen.length === SLOTS.length;
  const results = useMemo(() => (done ? seasonResults(profile(chosen), data.seasons, data.roles) : null), [done, chosen, data]);
  const best = useMemo(() => (done ? seasonResults(profile(bestFromDeal(dealt, data.roles)), data.seasons, data.roles) : null), [done, dealt, data]);

  if (error) return <Box sx={{ p: 2, color: colors.textLo }}>The draft couldn't load just now. Try again shortly.</Box>;
  if (!dealt) return <Box sx={{ p: 2, color: colors.textLo }}>Dealing…</Box>;
  const overseas = chosen.filter((c) => c.overseas).length;
  const made = results ? results.filter((r) => r.made).length : 0;

  return (
    <Box sx={{ maxWidth: 560, mx: 'auto', px: 2, pt: 1.5, pb: 4, color: colors.textHi, display: 'flex', flexDirection: 'column', gap: 1.5 }}>
      <Box>
        <Box sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 26 }}>Season Draft</Box>
        <Box sx={{ color: colors.textMed, fontSize: 13.5 }}>Pick eleven IPL player-seasons, three dealt per slot. Would your XI have made the playoffs?</Box>
      </Box>

      {!done && (
        <>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', ...mono, fontSize: 12, color: colors.textLo }}>
            <span>{`PICK ${chosen.length + 1} OF ${SLOTS.length} · ${SLOTS[chosen.length].label.toUpperCase()}`}</span>
            <span>{`${overseas}/${OVERSEAS_MAX} overseas`}</span>
          </Box>
          {dealt[chosen.length].map((c, n) => (
            <Card key={c.name} card={c} slot={SLOTS[chosen.length]} onPick={() => pick(n)} disabled={c.overseas && overseas >= OVERSEAS_MAX} />
          ))}
          <Box sx={{ fontSize: 11.5, color: colors.textLo }}>"× the season": his number against that season's league average for the role.</Box>
        </>
      )}

      {chosen.length > 0 && (
        <Box sx={{ bgcolor: colors.surface1, border: `1px solid ${colors.border}`, borderRadius: '14px', px: 1.5, py: 1 }}>
          {chosen.map((c, i) => (
            <Box key={c.name} sx={{ display: 'flex', justifyContent: 'space-between', fontSize: 13.5, py: 0.3 }}>
              <span>{`${i + 1}. ${c.name} ${c.season}`}</span>
              <Box component="span" sx={{ color: colors.textLo }}>{SLOTS[i].label}</Box>
            </Box>
          ))}
        </Box>
      )}

      {done && (
        <>
          <Box sx={{ textAlign: 'center', py: 1 }}>
            <Box sx={{ ...mono, fontSize: 44 }}>{`${made}/${results.length}`}</Box>
            <Box sx={{ fontSize: 15, color: colors.textMed }}>{`seasons your XI would have made the playoffs · topped ${results.filter((r) => r.topped).length}`}</Box>
          </Box>
          <Strip results={results} />
          <Box sx={{ fontSize: 13, color: colors.textMed }}>
            {`The best XI today's deal allowed: ${best.filter((r) => r.made).length}/${best.length}.`}
          </Box>
          <Box sx={{ fontSize: 11.5, color: colors.textLo }}>
            How scoring works: each pick's numbers against his season's league average for the role; in each season your
            XI is ranked among that season's real sides on those roles, and top four counts as making the playoffs. A game
            rule, not a prediction.
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Box component="button" type="button" onClick={restart}
              sx={{ all: 'unset', cursor: 'pointer', flex: 1, textAlign: 'center', py: 1.1, borderRadius: '12px', border: `1px solid ${colors.borderStrong}` }}>Draft again</Box>
            <Box component="button" type="button" onClick={() => {
              const url = window.location.href;
              const text = `Season Draft ${day}: my XI makes the IPL playoffs in ${made}/${results.length} seasons.`;
              if (navigator.share) navigator.share({ title: 'Season Draft', text, url }).catch(() => {}); else navigator.clipboard?.writeText(`${text} ${url}`);
            }} sx={{ all: 'unset', cursor: 'pointer', flex: 2, textAlign: 'center', py: 1.1, borderRadius: '12px', bgcolor: colors.accent, color: colors.bg, fontWeight: 600 }}>
              Share
            </Box>
          </Box>
        </>
      )}
    </Box>
  );
};

export default SeasonDraftGame;
