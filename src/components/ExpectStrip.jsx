import React from 'react';
import { Box, Typography } from '@mui/material';
import TakeawayCard, { TakeawayStrip } from './ui/TakeawayCard';
import { colors as hs, fonts } from '../theme/hindsightDark';
import { PHASE_COLORS } from '../theme/chartDefaults';
import { getTeamAbbr } from '../utils/teamAbbreviations';

const abbr = (team) => getTeamAbbr(team) || team;

const FormRow = ({ team, record }) => (
  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
    <Typography sx={{ fontWeight: 700, fontSize: 14, width: 44 }}>{abbr(team)}</Typography>
    {String(record || '').split('').map((r, i) => (
      <Box
        // eslint-disable-next-line react/no-array-index-key
        key={i}
        aria-label={r === 'W' ? 'won' : r === 'L' ? 'lost' : 'no result'}
        sx={{
          width: 24,
          height: 24,
          borderRadius: 1,
          display: 'grid',
          placeItems: 'center',
          fontFamily: fonts.mono,
          fontSize: 11,
          fontWeight: 600,
          bgcolor: r === 'W' ? 'rgba(12,163,12,0.22)' : r === 'L' ? 'rgba(230,103,103,0.18)' : 'rgba(255,255,255,0.08)',
          color: r === 'W' ? '#6fe06f' : r === 'L' ? '#f19a9a' : hs.textLo,
        }}
      >
        {r}
      </Box>
    ))}
  </Box>
);

const PHASE_KEYS = [['powerplay', 'Powerplay'], ['middle', 'Middle'], ['death', 'Death']];

/** How winning innings were built here: runs per phase, batting first v chasing, on one scale. */
const WinningPhases = ({ phases }) => {
  const rows = [['Won batting first', phases?.batting_first], ['Won chasing', phases?.chasing]].filter(([, v]) => v);
  if (!rows.length) return null;
  const max = Math.max(...rows.map(([, v]) => v.total || 0), 1);
  return (
    <Box sx={{ bgcolor: hs.surface1, border: `1px solid ${hs.border}`, borderRadius: 3, p: 1.75, display: 'grid', gap: 1.25 }}>
      <Box>
        <Typography sx={{ fontWeight: 700, fontSize: 15 }}>How winning innings were built</Typography>
        <Typography sx={{ fontSize: 13, color: hs.textLo }}>Average runs per phase in matches the side won</Typography>
      </Box>
      {rows.map(([label, v]) => (
        <Box key={label} sx={{ display: 'grid', gap: 0.5 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
            <span style={{ color: hs.textMed }}>{label}</span>
            <span style={{ fontFamily: fonts.mono, fontWeight: 600 }}>{v.total}</span>
          </Box>
          <Box sx={{ display: 'flex', height: 24, width: `${(v.total / max) * 100}%`, gap: '2px' }}>
            {PHASE_KEYS.map(([key], i) => (
              <Box
                key={key}
                sx={{
                  flex: `${v[key] || 0} 0 0`,
                  bgcolor: PHASE_COLORS[i],
                  borderRadius: i === 0 ? '4px 0 0 4px' : i === 2 ? '0 4px 4px 0' : 0,
                  display: 'flex',
                  alignItems: 'center',
                  pl: 0.75,
                  fontFamily: fonts.mono,
                  fontSize: 12,
                  fontWeight: 700,
                  color: '#0a0c11',
                  overflow: 'hidden',
                }}
              >
                {v[key]}
              </Box>
            ))}
          </Box>
        </Box>
      ))}
      <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap', fontSize: 12, color: hs.textLo }}>
        {PHASE_KEYS.map(([key, name], i) => (
          <span key={key}>
            <Box component="span" sx={{ display: 'inline-block', width: 10, height: 10, borderRadius: '3px', bgcolor: PHASE_COLORS[i], mr: 0.75, verticalAlign: '-1px' }} />
            {name}
          </span>
        ))}
      </Box>
    </Box>
  );
};

/**
 * "What to expect": the preview's answer as numbers, before any prose. Built from the `expect`
 * block of /match-preview (services/match_preview.build_expect_block).
 */
const ExpectStrip = ({ expect, team1, team2 }) => {
  if (!expect) return null;
  const { venue, form = [], head_to_head: h2h, lean, fantasy_top: fantasy = [], winning_phases: phases } = expect;

  const cards = [];
  if (venue) {
    cards.push(
      <TakeawayCard
        key="par"
        highlight
        label="Par score"
        value={venue.avg_winning_score ?? venue.avg_first_innings}
        unit={venue.avg_winning_score ? 'wins batting first' : 'average first innings'}
        caption={venue.avg_first_innings ? `The average first innings here is ${venue.avg_first_innings}.` : undefined}
        footnote={`Average winning first-innings total · ${venue.total_matches} matches`}
      />,
    );
    const chaseShare = venue.total_matches ? Math.round((venue.chasing_wins / venue.total_matches) * 100) : null;
    const tossValue = venue.toss_bias === 'chasing' ? 'Chase' : venue.toss_bias === 'bat_first' ? 'Bat first' : 'Even';
    cards.push(
      <TakeawayCard
        key="toss"
        label="Toss"
        value={tossValue}
        unit={`chasing won ${venue.chasing_wins} of ${venue.total_matches}`}
        caption={chaseShare != null ? `Chasing sides win ${chaseShare}% here.` : undefined}
        footnote={venue.highest_total_chased ? `Highest chase ${venue.highest_total_chased} · lowest defended ${venue.lowest_total_defended}` : undefined}
      />,
    );
  }
  if (form.some((f) => f.record)) {
    cards.push(
      <TakeawayCard key="form" label="Form · last 5" footnote="Most recent first">
        <Box sx={{ display: 'grid', gap: 0.75 }}>
          {form.filter((f) => f.record).map((f) => <FormRow key={f.team} team={f.team} record={f.record} />)}
        </Box>
      </TakeawayCard>,
    );
  }
  if (h2h?.sample_size) {
    const lead = h2h.team1_wins === h2h.team2_wins
      ? `Level ${h2h.team1_wins}–${h2h.team2_wins}`
      : h2h.team1_wins > h2h.team2_wins
        ? `${abbr(team1)} ${h2h.team1_wins}–${h2h.team2_wins}`
        : `${abbr(team2)} ${h2h.team2_wins}–${h2h.team1_wins}`;
    cards.push(
      <TakeawayCard key="h2h" label="Head to head" value={lead} unit={`last ${h2h.sample_size}`} footnote="In the selected window" />,
    );
  }
  if (lean?.label) {
    cards.push(
      <TakeawayCard
        key="lean"
        label="Hindsight's lean"
        value={lean.winner ? abbr(lean.winner) : 'Even'}
        unit={lean.label.replace(lean.winner || '', '').trim() || undefined}
        caption={lean.reasons?.length ? lean.reasons.join(' · ') : undefined}
        footnote="From form, H2H, Elo, venue fit and matchups"
      />,
    );
  }
  if (fantasy.length) {
    cards.push(
      <TakeawayCard key="fantasy" label="Fantasy picks" footnote="Expected fantasy points">
        <Box component="ol" sx={{ m: 0, p: 0, listStyle: 'none', display: 'grid', gap: 0.5 }}>
          {fantasy.slice(0, 3).map((p) => (
            <Box component="li" key={p.player} sx={{ display: 'flex', gap: 1, fontSize: 14 }}>
              <Box component="span" sx={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {p.player} <Box component="span" sx={{ color: hs.textFaint, fontSize: 12 }}>{abbr(p.team)}</Box>
              </Box>
              <Box component="span" sx={{ fontFamily: fonts.mono, fontWeight: 600 }}>{p.expected_points}</Box>
            </Box>
          ))}
        </Box>
      </TakeawayCard>,
    );
  }

  if (!cards.length && !phases) return null;

  return (
    <Box sx={{ display: 'grid', gap: 1.5 }}>
      {cards.length > 0 && <TakeawayStrip columns={3}>{cards}</TakeawayStrip>}
      <WinningPhases phases={phases} />
    </Box>
  );
};

export default ExpectStrip;
