import React, { useMemo, useState } from 'react';
import { Box, ButtonBase, Typography } from '@mui/material';
import { colors as hs, fonts } from '../theme/hindsightDark';
import { DIVERGING } from '../theme/chartDefaults';
import DetailSheet from './ui/DetailSheet';

export const MIN_BATTLE_BALLS = 12;
const SR_SCALE = 120; // strike-rate points to the end of a half-bar

const rate = (wickets, balls) => (balls > 0 ? wickets / balls : 0);

/**
 * Rank batter-v-bowler pairs by how lopsided they are.
 *
 * `sides` is [{ battingTeam, bowlingTeam, matchups }] where matchups is the /teams/{t1}/{t2}/matchups
 * shape: matchups[batter][bowler] = { balls, runs, wickets, strike_rate, ... } plus
 * matchups[batter].Overall = that batter against the whole attack, which is the baseline.
 *
 * Score = sqrt(balls) x (strike-rate gap / 100 + dismissal-rate gap per 20 balls), so a big edge
 * over a real sample outranks a freak 12-ball one. The edge label weighs both: scoring faster but
 * getting out much more often is a trade-off, not a batter's edge.
 */
export const rankBattles = (sides, { minBalls = MIN_BATTLE_BALLS, limit = 8 } = {}) => {
  const battles = [];
  sides.forEach(({ battingTeam, bowlingTeam, matchups }) => {
    Object.entries(matchups || {}).forEach(([batter, row]) => {
      const base = row?.Overall;
      if (!base || !base.balls) return;
      const baseSr = Number(base.strike_rate) || (base.runs * 100) / base.balls;
      const baseOut = rate(base.wickets || 0, base.balls);
      Object.entries(row).forEach(([bowler, m]) => {
        if (bowler === 'Overall' || !m || (m.balls || 0) < minBalls) return;
        const sr = Number(m.strike_rate) || (m.runs * 100) / m.balls;
        const srGap = sr - baseSr;
        const out = rate(m.wickets || 0, m.balls);
        const outGap = (out - baseOut) * 20;
        let edge;
        if (srGap > 0 && out <= baseOut * 1.25) edge = 'batter';
        else if (srGap < 0 && out >= baseOut * 0.75) edge = 'bowler';
        else edge = 'trade-off';
        battles.push({
          batter,
          bowler,
          battingTeam,
          bowlingTeam,
          balls: m.balls,
          runs: m.runs,
          wickets: m.wickets || 0,
          sr,
          baseSr,
          srGap,
          dots: m.dot_percentage,
          boundaries: m.boundary_percentage,
          ballsPerOut: m.wickets ? m.balls / m.wickets : null,
          baseBallsPerOut: base.wickets ? base.balls / base.wickets : null,
          edge,
          score: Math.sqrt(m.balls) * (Math.abs(srGap) / 100 + Math.abs(outGap)),
        });
      });
    });
  });
  return battles.sort((a, b) => b.score - a.score).slice(0, limit);
};

const EDGE_STYLE = {
  batter: { label: 'Batter edge', color: '#9cc3f5', bg: 'rgba(57,135,229,0.16)' },
  bowler: { label: 'Bowler edge', color: '#f2a3a3', bg: 'rgba(230,103,103,0.16)' },
  'trade-off': { label: 'Trade-off', color: hs.textMed, bg: 'rgba(255,255,255,0.08)' },
};

const GapBar = ({ gap }) => {
  const width = (Math.min(Math.abs(gap), SR_SCALE) / SR_SCALE) * 50;
  return (
    <Box sx={{ position: 'relative', height: 14, my: 0.25 }} aria-hidden="true">
      <Box sx={{ position: 'absolute', inset: '4px 0', borderRadius: 4, bgcolor: 'rgba(255,255,255,0.05)' }} />
      <Box
        sx={{
          position: 'absolute',
          top: 2,
          height: 10,
          borderRadius: 1,
          left: gap >= 0 ? '50%' : `${50 - width}%`,
          width: `${width}%`,
          bgcolor: gap >= 0 ? DIVERGING.positive : DIVERGING.negative,
        }}
      />
      <Box sx={{ position: 'absolute', left: '50%', top: 0, bottom: 0, width: '2px', ml: '-1px', bgcolor: hs.textLo }} />
    </Box>
  );
};

const fmt1 = (v) => (v == null ? 'none' : v.toFixed(1));

/**
 * The phone-first replacement for reading the batter x bowler matrices: the most lopsided pairs as
 * cards, each tappable for the full numbers. The matrices stay available below.
 */
const KeyBattles = ({ sides }) => {
  const battles = useMemo(() => rankBattles(sides), [sides]);
  const [open, setOpen] = useState(null);

  if (!battles.length) return null;

  return (
    <Box sx={{ bgcolor: 'background.paper', border: 1, borderColor: 'divider', borderRadius: 2, p: 2, mb: 3 }}>
      <Typography sx={{ fontWeight: 700, fontSize: 17 }}>Key battles</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        Strike rate against this bowler v against the whole attack · {MIN_BATTLE_BALLS}+ balls
      </Typography>
      {battles.map((b, i) => {
        const style = EDGE_STYLE[b.edge];
        return (
          <ButtonBase
            key={`${b.batter}-${b.bowler}`}
            onClick={() => setOpen(b)}
            sx={{
              display: 'block',
              width: '100%',
              textAlign: 'left',
              py: 1.25,
              borderTop: i ? `1px solid ${hs.border}` : 'none',
              borderRadius: 1,
              '&:focus-visible': { outline: `2px solid ${hs.accent}` },
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography sx={{ fontSize: 14, minWidth: 0, flex: 1 }}>
                <Box component="span" sx={{ fontWeight: 600 }}>{b.batter}</Box>
                <Box component="span" sx={{ color: hs.textFaint, fontSize: 12, mx: 0.75 }}>v</Box>
                <Box component="span" sx={{ fontWeight: 600 }}>{b.bowler}</Box>
              </Typography>
              <Box sx={{ flexShrink: 0, fontFamily: fonts.mono, fontSize: 11, px: 1, py: 0.25, borderRadius: 99, color: style.color, bgcolor: style.bg }}>
                {style.label}
              </Box>
            </Box>
            <GapBar gap={b.srGap} />
            <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap', fontFamily: fonts.mono, fontSize: 12, color: hs.textLo }}>
              <span>{b.runs} off {b.balls}</span>
              <span>{b.wickets} out</span>
              <span>SR {Math.round(b.sr)} v {Math.round(b.baseSr)}</span>
            </Box>
          </ButtonBase>
        );
      })}
      <DetailSheet
        open={Boolean(open)}
        onClose={() => setOpen(null)}
        title={open ? `${open.batter} v ${open.bowler}` : ''}
        subtitle={open ? `${open.battingTeam} batting` : ''}
        rows={open ? [
          { label: 'Runs / balls', value: `${open.runs} / ${open.balls}` },
          { label: 'Dismissals', value: open.wickets },
          { label: 'Strike rate', value: open.sr.toFixed(1), hint: `${open.baseSr.toFixed(1)} v whole attack` },
          { label: 'Balls per dismissal', value: fmt1(open.ballsPerOut), hint: `${fmt1(open.baseBallsPerOut)} v whole attack` },
          { label: 'Dot %', value: open.dots != null ? `${Number(open.dots).toFixed(0)}%` : '–' },
          { label: 'Boundary %', value: open.boundaries != null ? `${Number(open.boundaries).toFixed(0)}%` : '–' },
        ] : []}
      />
    </Box>
  );
};

export default KeyBattles;
