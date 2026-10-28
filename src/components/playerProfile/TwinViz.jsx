import React, { useState } from 'react';
import { Box, Tooltip } from '@mui/material';
import { colors, fonts } from '../../theme/hindsightDark';

// Statistical twins visuals (DOPPELGANGER_PLAN.md S6).
//   TwinMap: the player at the centre, his nearest players at their true distance (rings at 10-point steps); the
//            angle comes from how alike they are to each other (MDS), so similar players sit on the same side.
//   TwinCompare: both players' percentiles on every feature compared, grouped, the player in lime.

const TWIN = '#e6e8ec'; // the twin's dot: light ink, distinct from the player's lime
const W = 343;

const GROUP_NAMES = {
  usage: 'Usage', scoring: 'Scoring shape', shots: 'Shot mix', matchups: 'Pace and spin',
  lengths: 'Lengths', lines: 'Lines', outcomes: 'Outcomes',
};
const groupName = (g) => {
  const [role, name] = g.includes(':') ? g.split(':') : [null, g];
  const base = GROUP_NAMES[name] || name;
  return role ? `${base} (${role === 'bat' ? 'bat' : 'ball'})` : base;
};

// Surname, or the first name for a common surname ("Rashid", not "Khan"): the user's naming rule.
const COMMON_SURNAMES = new Set(['Sharma', 'Yadav', 'Singh', 'Kumar', 'Patel', 'Khan', 'Iyer', 'Pandya']);
const short = (name) => {
  const parts = name.split(' ');
  const last = parts[parts.length - 1];
  return parts.length > 1 && !COMMON_SURNAMES.has(last) ? last : parts[0];
};

export const TwinMap = ({ player, points, highlight = 5 }) => {
  if (!points?.length) return null;
  const max = Math.max(...points.map((p) => p.distance));
  const outer = Math.ceil(max * 10) / 10;
  const R = 148;
  const c = W / 2;
  const rings = [];
  for (let r = 0.1; r <= outer + 1e-9; r += 0.1) rings.push(Number(r.toFixed(1)));
  const pos = (p) => {
    const rr = (p.distance / outer) * R;
    const a = (p.angle * Math.PI) / 180;
    return [c + rr * Math.cos(a), c - rr * Math.sin(a)];
  };
  return (
    <svg viewBox={`0 0 ${W} ${W}`} width="100%" role="img" aria-label={`The players closest to ${player}`} style={{ display: 'block', maxWidth: 420, margin: '0 auto' }}>
      {rings.map((r) => (
        <g key={r}>
          <circle cx={c} cy={c} r={(r / outer) * R} fill="none" stroke={colors.borderStrong} strokeDasharray="3 4" />
          <text x={c} y={c - (r / outer) * R - 3} textAnchor="middle" fill={colors.textFaint} fontSize="9" fontFamily={fonts.mono}>
            {Math.round(r * 100)} pts
          </text>
        </g>
      ))}
      {points.slice().reverse().map((p, ri) => {
        const i = points.length - 1 - ri;
        const [x, y] = pos(p);
        const top = i < highlight;
        return (
          <Tooltip key={`${p.player}-${p.period}`} enterTouchDelay={0} title={`${p.player}: ${Math.round(p.distance * 100)} points apart`}>
            <g>
              <circle cx={x} cy={y} r={top ? 5.5 : 4} fill={top ? TWIN : colors.textLo}
                opacity={top ? 1 : Math.max(0.35, 0.9 - i * 0.025)} stroke={colors.bg} strokeWidth="1.5" />
              {top && (
                <text x={x + (x > c ? 8 : -8)} y={y + 4} textAnchor={x > c ? 'start' : 'end'} fill={colors.textHi}
                  fontSize="11" fontFamily={fonts.body} fontWeight="600">{short(p.player)}</text>
              )}
            </g>
          </Tooltip>
        );
      })}
      <circle cx={c} cy={c} r="7" fill={colors.accent} stroke={colors.bg} strokeWidth="2" />
      <text x={c} y={c + 20} textAnchor="middle" fill={colors.accent} fontSize="11.5" fontFamily={fonts.display} fontWeight="700">{short(player)}</text>
    </svg>
  );
};

export const TwinCompare = ({ player, twin, rows }) => {
  const [open, setOpen] = useState(false);
  if (!rows?.length) return null;
  const groups = [];
  rows.forEach((r) => {
    const last = groups[groups.length - 1];
    if (last && last.group === r.group) last.rows.push(r);
    else groups.push({ group: r.group, rows: [r] });
  });
  const LW = 128;
  const track = (v) => LW + 8 + (v / 100) * (W - LW - 16);
  return (
    <Box>
      <Box component="button" onClick={() => setOpen(!open)} aria-expanded={open}
        sx={{ all: 'unset', cursor: 'pointer', fontSize: 12, color: colors.accent, '&:focus-visible': { outline: `2px solid ${colors.accent}` } }}>
        {open ? 'Hide the comparison' : `Compare all ${rows.length} features`}
      </Box>
      {open && (
        <Box sx={{ mt: 1, display: 'flex', flexDirection: 'column', gap: 1 }}>
          <Box sx={{ display: 'flex', gap: 1.5, fontSize: 11.5, color: colors.textLo }}>
            <span><Box component="i" sx={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', bgcolor: colors.accent, mr: 0.5 }} />{player}</span>
            <span><Box component="i" sx={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', bgcolor: TWIN, mr: 0.5 }} />{twin}</span>
            <span>· percentile, 0 to 100</span>
          </Box>
          {groups.map((g) => (
            <Box key={g.group}>
              <Box sx={{ fontFamily: fonts.mono, fontSize: 9.5, letterSpacing: '0.1em', textTransform: 'uppercase', color: colors.textLo, mb: 0.25 }}>
                {groupName(g.group)}
              </Box>
              <svg viewBox={`0 0 ${W} ${g.rows.length * 18}`} width="100%" aria-hidden="true" style={{ display: 'block' }}>
                {g.rows.map((r, i) => {
                  const y = i * 18 + 9;
                  const text = r.label.replace(/ \((bat|ball)\)$/, '');
                  return (
                    <g key={r.feature}>
                      <text x="0" y={y + 3.5} fill={colors.textMed} fontSize="10.5" fontFamily={fonts.body}>
                        {text.length > 24 ? `${text.slice(0, 23)}…` : text}
                      </text>
                      <line x1={track(0)} x2={track(100)} y1={y} y2={y} stroke={colors.surface2} strokeWidth="2" />
                      <line x1={track(50)} x2={track(50)} y1={y - 4} y2={y + 4} stroke={colors.textGhost} />
                      <line x1={track(r.player)} x2={track(r.twin)} y1={y} y2={y} stroke={colors.textLo} strokeWidth="1.5" />
                      <circle cx={track(r.twin)} cy={y} r="4" fill={TWIN} stroke={colors.bg} strokeWidth="1.5" />
                      <circle cx={track(r.player)} cy={y} r="4" fill={colors.accent} stroke={colors.bg} strokeWidth="1.5" />
                    </g>
                  );
                })}
              </svg>
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );
};
