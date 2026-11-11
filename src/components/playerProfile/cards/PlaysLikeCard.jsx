import React, { useEffect, useState } from 'react';
import { Box, Skeleton } from '@mui/material';
import { Link } from 'react-router-dom';
import ExpandMoreRoundedIcon from '@mui/icons-material/ExpandMoreRounded';
import config from '../../../config';
import { colors, fonts } from '../../../theme/hindsightDark';
import { TwinCompare } from '../TwinViz';
import ProfileCard from './ProfileCard';

// "Plays like" on the simplified profile (PROFILE_SIMPLIFY_PLAN.md P5): the four closest twins from GET /twins/{name}
// for the page's period, each a row with its two closest traits; the lime chevron opens the full comparison.

const TRAIT_SHORT = {
  'powerplay strike rate': 'powerplay SR', 'strike rate v spin': 'SR v spin', 'strike rate v pace': 'SR v pace',
  'middle-overs strike rate': 'middle-overs SR', 'sixes among boundaries': 'six share', 'short of a good length': 'back of length',
  'outside offstump': 'off-stump line', 'wide outside offstump': 'wide line', 'batting position': 'batting spot', 'death share': 'death overs',
};
const traits = (closest) => (closest || []).slice(0, 2).map((c) => {
  const label = c.label || '';
  const role = / \((bat|ball)\)$/.exec(label);
  const base = label.replace(/ \((bat|ball)\)$/, '');
  return (TRAIT_SHORT[base] || base) + (role ? ` (${role[1]})` : '');
}).join(', ');

const valueText = (key, v) => {
  if (v === null || v === undefined) return '–';
  const s = (x, d) => `${x > 0 ? '+' : x < 0 ? '−' : ''}${Math.abs(x).toFixed(d)}`;
  if (key === 'wpa_per_innings') return s(v, 3);
  if (key === 'raa_per_100') return s(v, 1);
  if (key === 'economy') return v.toFixed(2);
  return `${v.toFixed(1)}${key.endsWith('pct') ? '%' : ''}`;
};

const KIND = { bat: 'batters', bowl: 'bowlers', allround: 'all-rounders' };

const PlaysLikeCard = ({ player, unit }) => {
  const [state, setState] = useState({ status: 'loading', data: null });
  const [open, setOpen] = useState(null);

  useEffect(() => {
    if (!player) return undefined;
    let cancelled = false;
    setState({ status: 'loading', data: null });
    setOpen(null);
    fetch(`${config.API_URL}/twins/${encodeURIComponent(player)}?n=4&unit=${unit}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((data) => { if (!cancelled) setState({ status: 'ready', data }); })
      .catch(() => { if (!cancelled) setState({ status: 'none', data: null }); });
    return () => { cancelled = true; };
  }, [player, unit]);

  if (state.status === 'loading') return <Skeleton variant="rounded" height={190} sx={{ bgcolor: colors.surface2, borderRadius: '18px' }} />;
  const d = state.data;
  if (state.status !== 'ready' || !d?.twins?.length) return null;

  return (
    <ProfileCard id="plays-like" title={d.unique ? 'No close twin' : 'Plays like'} player={player}
      note={`How he plays, as percentiles among ${KIND[d.role] || 'players'}`}>
      <Box component="ul" sx={{ listStyle: 'none', m: 0, p: 0 }}>
        {d.twins.slice(0, 4).map((t) => {
          const expanded = open === t.player;
          return (
            <Box component="li" key={t.player} sx={{ borderBottom: `1px solid ${colors.border}`, py: 1 }}>
              <Box sx={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto 32px', alignItems: 'center', columnGap: 1 }}>
                <Box component={Link} to={`/player?name=${encodeURIComponent(t.player)}`}
                  sx={{ fontWeight: 600, fontSize: 15, color: colors.textHi, textDecoration: 'none', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', minHeight: 32, display: 'flex', alignItems: 'center' }}>
                  {t.player}
                </Box>
                <Box component="span" sx={{ fontFamily: fonts.mono, fontSize: 11.5, color: colors.textLo, whiteSpace: 'nowrap' }}>{`${t.gap_points} pts apart`}</Box>
                <Box component="button" type="button" aria-expanded={expanded} aria-label={`Compare with ${t.player}`}
                  onClick={() => setOpen(expanded ? null : t.player)}
                  sx={{ all: 'unset', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 32, height: 32, color: colors.accent, borderRadius: '50%', justifySelf: 'end',
                    transform: expanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s',
                    '&:focus-visible': { outline: `2px solid ${colors.accent}`, outlineOffset: 2 } }}>
                  <ExpandMoreRoundedIcon fontSize="small" />
                </Box>
              </Box>
              {t.closest?.length > 0 && (
                <Box sx={{ fontSize: 12, color: colors.textLo, mt: 0.25, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {`Same: ${traits(t.closest)}`}
                </Box>
              )}
              {expanded && (
                <Box sx={{ mt: 1.25, display: 'flex', flexDirection: 'column', gap: 1.25 }}>
                  <Box sx={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto auto', columnGap: 1.5, rowGap: 0.25, fontSize: 12, fontVariantNumeric: 'tabular-nums' }}>
                    <Box />
                    <Box sx={{ color: colors.textLo, textAlign: 'right' }}>{player.split(' ').slice(-1)[0]}</Box>
                    <Box sx={{ color: colors.textLo, textAlign: 'right' }}>{t.player.split(' ').slice(-1)[0]}</Box>
                    {(t.values || []).map((v) => (
                      <React.Fragment key={`${v.role}-${v.key}`}>
                        <Box sx={{ color: colors.textLo, whiteSpace: 'nowrap' }}>{v.label}{d.role === 'allround' ? (v.role === 'bat' ? ' (bat)' : ' (ball)') : ''}</Box>
                        <Box sx={{ textAlign: 'right' }}>{valueText(v.key, v.player)}</Box>
                        <Box sx={{ textAlign: 'right' }}>{valueText(v.key, v.twin)}</Box>
                      </React.Fragment>
                    ))}
                  </Box>
                  <TwinCompare player={player} twin={t.player} rows={t.compare} alwaysOpen />
                </Box>
              )}
            </Box>
          );
        })}
      </Box>
    </ProfileCard>
  );
};

export default PlaysLikeCard;
