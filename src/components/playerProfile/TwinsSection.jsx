import React, { useEffect, useRef, useState } from 'react';
import { Box, Skeleton, Tooltip } from '@mui/material';
import { Link } from 'react-router-dom';
import config from '../../config';
import { colors, fonts } from '../../theme/hindsightDark';
import { TwinCompare, TwinMap } from './TwinViz';

// "Plays like" (DOPPELGANGER_PLAN.md S5): the players whose game is closest over the last few seasons against strong
// sides, from GET /twins/{name}. Matched on style only (usage, scoring shape, shot mix, matchups; for bowlers usage,
// lengths, lines, outcomes). Value is shown side by side, never matched on: Impact and wins added don't repeat from
// one half of a sample to the other, so a "worth like" twin would be noise. Renders `fallback` when the player
// isn't in the pool.

const fmt = (key, v) => {
  if (v === null || v === undefined) return '–';
  if (key === 'wpa_per_innings' && Math.abs(v) < 0.0005) return '0.000';
  if (key === 'wpa_per_innings') return `${v > 0 ? '+' : v < 0 ? '−' : ''}${Math.abs(v).toFixed(3)}`;
  if (key === 'raa_per_100') return `${v > 0 ? '+' : v < 0 ? '−' : ''}${Math.abs(v).toFixed(1)}`;
  if (key === 'economy') return v.toFixed(2);
  return `${v.toFixed(1)}${key.endsWith('pct') ? '%' : ''}`;
};

// First names for common surnames ("Hardik", not "Pandya"; the user's naming rule for cards).
const COMMON_SURNAMES = new Set(['Sharma', 'Yadav', 'Singh', 'Kumar', 'Patel', 'Khan', 'Iyer', 'Pandya']);
const surname = (name) => {
  const parts = name.split(' ');
  const last = parts[parts.length - 1];
  return COMMON_SURNAMES.has(last) ? parts[0] : last;
};

const UNITS = [['window', 'Recent'], ['career', 'Career']];

const TwinsSection = ({ playerName, fallback }) => {
  const [state, setState] = useState({ status: 'loading', data: null });
  // Recent (since 2024) by default; a player not in that pool tries Career (since 2015) before the fallback.
  const [unit, setUnit] = useState('window');
  const autoCareer = useRef(false);

  useEffect(() => {
    if (!playerName) return undefined;
    let cancelled = false;
    setState({ status: 'loading', data: null });
    fetch(`${config.API_URL}/twins/${encodeURIComponent(playerName)}?n=5&unit=${unit}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((data) => { if (!cancelled) setState({ status: 'ready', data }); })
      .catch(() => {
        if (cancelled) return;
        if (unit === 'window' && !autoCareer.current) {
          autoCareer.current = true;
          setUnit('career');
        } else {
          setState({ status: 'none', data: null });
        }
      });
    return () => { cancelled = true; };
  }, [playerName, unit]);

  const unitSwitch = (
    <Box role="tablist" aria-label="Period" sx={{ display: 'inline-flex', alignSelf: 'flex-start', border: `1px solid ${colors.borderStrong}`, borderRadius: '999px', p: '2px' }}>
      {UNITS.map(([key, name]) => (
        <Box key={key} component="button" role="tab" aria-selected={key === unit} onClick={() => setUnit(key)}
          sx={{
            all: 'unset', cursor: 'pointer', fontFamily: fonts.display, fontWeight: 600, fontSize: 12.5, px: 1.4, py: '2px',
            borderRadius: '999px', bgcolor: key === unit ? colors.textHi : 'transparent', color: key === unit ? colors.bg : colors.textLo,
            '&:focus-visible': { outline: `2px solid ${colors.accent}`, outlineOffset: 2 },
          }}>
          {name}
        </Box>
      ))}
    </Box>
  );

  if (state.status === 'loading') return <Skeleton variant="rounded" height={160} sx={{ bgcolor: colors.surface2 }} />;
  if (state.status !== 'ready' || !state.data.twins?.length) {
    // A player who has a pool on one side gets the switch to try the other.
    return autoCareer.current ? <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>{unitSwitch}{fallback || null}</Box>
      : (fallback || null);
  }

  const d = state.data;
  const [from, to] = (d.period || '').split('..');
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
      {unitSwitch}
      <Box>
        <Box sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 18 }}>{d.unique ? 'No close twin' : 'Plays like'}</Box>
        {d.unique && (
          <Box sx={{ color: colors.textMed, fontSize: 13.5, mt: 0.5 }}>
            {`The nearest, ${d.twins[0].player}, is ${d.twins[0].gap_points} points apart; most players have one within ${d.typical_gap_points}.`}
          </Box>
        )}
        <Box sx={{ color: colors.textLo, fontSize: 12.5 }}>
          {`Closest games among ${d.pool} ${d.role === 'bowl' ? 'bowlers' : d.role === 'allround' ? 'all-rounders' : 'batters'}`}
          {from ? `, ${from.slice(0, 4)} to ${to ? to.slice(0, 4) : 'now'}` : ''} · major leagues and top-12 T20Is
        </Box>
      </Box>
      {d.map?.length > 0 && <TwinMap player={d.player} points={d.map} highlight={d.unique ? 3 : 5} />}
      {d.twins.map((t, i) => (
        <Box key={t.player} sx={{ bgcolor: colors.surface1, border: `1px solid ${i === 0 && !d.unique ? 'rgba(182,242,74,0.45)' : colors.border}`, borderRadius: '14px', p: 1.5, display: 'flex', flexDirection: 'column', gap: 1 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 1 }}>
            <Box component={Link} to={`/player?name=${encodeURIComponent(t.player)}&autoload=true`}
              sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 17, color: colors.textHi, textDecoration: 'none', '&:hover': { color: colors.accent } }}>
              {t.player}
            </Box>
            <Tooltip enterTouchDelay={0} title="The typical gap between the two players' percentiles across the features compared: lower is closer.">
              <Box component="span" sx={{ fontFamily: fonts.mono, fontSize: 11, color: i === 0 && !d.unique ? colors.accent : colors.textLo, whiteSpace: 'nowrap' }}>
                {t.gap_points} pts apart
              </Box>
            </Tooltip>
          </Box>
          {t.closest?.length > 0 && (
            <Box sx={{ fontSize: 12.5, color: colors.textMed }}>
              <Box component="span" sx={{ color: colors.textLo }}>Same: </Box>
              {t.closest.map((c) => c.label).join(', ')}
            </Box>
          )}
          {t.furthest?.length > 0 && (
            <Box sx={{ fontSize: 12.5, color: colors.textMed }}>
              <Box component="span" sx={{ color: colors.textLo }}>Different: </Box>
              {t.furthest[0].label}
            </Box>
          )}
          <Box sx={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto auto', columnGap: 1.5, rowGap: 0.25, fontSize: 12, fontVariantNumeric: 'tabular-nums' }}>
            <Box />
            <Box sx={{ color: colors.textLo, textAlign: 'right' }}>{surname(d.player)}</Box>
            <Box sx={{ color: colors.textLo, textAlign: 'right' }}>{surname(t.player)}</Box>
            {t.values.map((v) => (
              <React.Fragment key={`${v.role}-${v.key}`}>
                <Box sx={{ color: colors.textLo }}>{v.label}{d.role === 'allround' ? (v.role === 'bat' ? ' (bat)' : ' (ball)') : ''}</Box>
                <Box sx={{ textAlign: 'right', color: colors.textHi }}>{fmt(v.key, v.player)}</Box>
                <Box sx={{ textAlign: 'right', color: colors.textHi }}>{fmt(v.key, v.twin)}</Box>
              </React.Fragment>
            ))}
          </Box>
          <TwinCompare player={d.player} twin={t.player} rows={t.compare} />
        </Box>
      ))}
    </Box>
  );
};

export default TwinsSection;
