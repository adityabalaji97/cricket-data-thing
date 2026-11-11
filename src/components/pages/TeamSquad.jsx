import React, { useEffect, useState } from 'react';
import { Box } from '@mui/material';

import config from '../../config';
import { colors } from '../../theme/hindsightDark';
import ProfileCard from '../playerProfile/cards/ProfileCard';
import { POST_VISUALS } from '../story/postVisuals';
import { Eyebrow } from '../pageKit/pageKit';
import PlayerLink from '../common/PlayerLink';

// The team page's Squad group (XI_BUILDER_PLAN.md X3): the IPL retention post's four squad cards, from the same build
// (GET /team-squad, services/squad_view.py), so the page and the post never disagree. IPL sides only; hidden otherwise.

const NAMES = { board: 'Squad', template: "Against the winners' template", value: 'Price v wins added', cases: 'Three calls' };
// What the copy calls a player: the surname, or the first name where the surname is shared by many (the retention
// posts' called(): "Arshdeep", not "Singh").
const COMMON = new Set(['Ahmed', 'Ahmad', 'Khan', 'Singh', 'Sharma', 'Kumar', 'Yadav', 'Patel', 'Pandya', 'Iyer']);
const surname = (n) => { const w = n.split(' '); return w.length > 1 && COMMON.has(w[w.length - 1]) ? w[0] : w[w.length - 1]; };

const dealLine = (d) => `${d.ins.map(surname).join(', ')} in, ${d.outs.map(surname).join(', ')} out`
  + (/awaiting/.test(d.source || '') ? ' · awaiting BCCI' : '');

const FMT = { average: (v) => v.toFixed(1), strike_rate: (v) => v.toFixed(0), wickets_per_24: (v) => v.toFixed(2), economy: (v) => v.toFixed(2) };
const UNIT = { average: 'avg', strike_rate: 'SR', wickets_per_24: 'wkts / 4 ov', economy: 'an over' };

/** Who fits a gap (XI_BUILDER_PLAN.md X4a, X4c): what fits (playoff sides' level and two proven examples, who are
 * examples, not options), then the auction pool: on their IPL record, then on all T20s for those the IPL hasn't seen
 * enough of (not yet adjusted for strength: X4d). */
const FitBody = ({ fit }) => {
  const f = FMT[fit.measure];
  const u = UNIT[fit.measure];
  const row = (x, sub) => (
    <Box key={x.name} sx={{ display: 'grid', gridTemplateColumns: '1fr auto', alignItems: 'baseline', gap: 1, py: 0.5 }}>
      <Box sx={{ minWidth: 0 }}>
        <Box sx={{ fontSize: 14, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}><PlayerLink name={x.name} /></Box>
        <Box sx={{ fontSize: 11, color: colors.textLo, whiteSpace: 'nowrap' }}>{`${x.balls} balls${sub}`}</Box>
      </Box>
      <Box sx={{ fontSize: 14, fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' }}>{`${f(x.value)} ${u}`}</Box>
    </Box>
  );
  const like = (fit.examples || []).map((x) => `${x.name.split(' ').slice(-1)[0]} ${f(x.value)}`).join(', ');
  const empty = !fit.free.length && !(fit.outside || []).length;
  return (
    <>
      <Box sx={{ fontSize: 13, color: colors.textMed, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', mb: 1 }}>
        {`Playoff sides ${f(fit.playoff_level)} ${u}${like ? ` · like ${like}` : ''}`}
      </Box>
      {fit.free.length > 0 && <><Eyebrow>In the auction pool · IPL record</Eyebrow>{fit.free.map((x) => row(x, ' in the IPL'))}</>}
      {(fit.outside || []).length > 0 && (
        <Box sx={{ mt: fit.free.length ? 1 : 0 }}><Eyebrow>In the auction pool · all T20s</Eyebrow>{fit.outside.map((x) => row(x, ' in T20s'))}</Box>
      )}
      {empty && <Box sx={{ fontSize: 13.5, color: colors.textLo, py: 1 }}>Nobody in the auction pool does it yet. The released lists land on 17 Nov.</Box>}
    </>
  );
};

// One "Who fits" card with a switch between the gaps, not a card per gap (four near-identical cards made CSK's page
// 7.5 phone screens: 13 Nov 2026 audit).
const FitsCard = ({ team, fits }) => {
  const [k, setK] = useState(0);
  const fit = fits[Math.min(k, fits.length - 1)];
  const f = FMT[fit.measure];
  return (
    <ProfileCard id="fits" title="Who fits the gaps" player={team}
      note={`Theirs ${fit.squad_value != null ? f(fit.squad_value) : '–'} · IPL 2024-26 · all T20s not strength-adjusted`}>
      {fits.length > 1 && (
        <Box role="tablist" aria-label="Gap" sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75, mb: 1.25 }}>
          {fits.map((x, i) => (
            <Box key={x.key} component="button" type="button" role="tab" aria-selected={i === k} onClick={() => setK(i)}
              sx={{ all: 'unset', cursor: 'pointer', minHeight: 32, boxSizing: 'border-box', display: 'inline-flex', alignItems: 'center', px: 1.25,
                borderRadius: '999px', fontSize: 13, border: `1px solid ${i === k ? colors.accent : colors.borderStrong}`,
                color: i === k ? colors.bg : colors.textMed, bgcolor: i === k ? colors.accent : 'transparent',
                '&:focus-visible': { outline: `2px solid ${colors.accent}`, outlineOffset: 2 } }}>
              {x.label}
            </Box>
          ))}
        </Box>
      )}
      <FitBody fit={fit} />
    </ProfileCard>
  );
};

const TeamSquad = ({ team }) => {
  const [data, setData] = useState(null);
  useEffect(() => {
    let cancelled = false;
    setData(null);
    fetch(`${config.API_URL}/team-squad?team=${encodeURIComponent(team)}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (!cancelled) setData(d); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [team]);
  if (!data?.cards?.length) return null;
  const asOf = new Date(data.as_of).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.75 }}>
      {/* Fix my team is The XI card's header action (13 Nov 2026), not a banner here. */}
      <Eyebrow right={<Box component="span" sx={{ fontSize: 11, color: colors.textLo }}>{`as of ${asOf}`}</Box>}>IPL 2027 squad</Eyebrow>
      {data.cards.map((c) => {
        const Visual = POST_VISUALS[c.visual];
        if (!Visual) return null;
        // The squad card's note is one line on the page: the trades, else how many have barely played (the slide's
        // longer note, with names, wrapped at phone width).
        const board = c.id === 'board';
        const quiet = board ? (c.payload.note || '').match(/Barely played since 2025 \(under 10 balls\): (\d+)/) : null;
        const note = board
          ? (data.deals?.length ? data.deals.map(dealLine).join(' · ') : quiet ? `${quiet[1]} have barely played since 2025` : c.sample)
          : c.id === 'template' ? 'IPL 2024-26 at any side · v playoff sides 2023-26' : c.sample;
        const payload = { ...c.payload, ...(board ? { note: null } : {}), page: true };
        return (
          <ProfileCard key={c.id} id={`squad-${c.id}`} title={NAMES[c.id] || c.kicker} player={team} note={note}>
            <Box sx={{ mx: -0.5 }}><Visual payload={payload} /></Box>
          </ProfileCard>
        );
      })}
      {(data.fits || []).length > 0 && <FitsCard team={team} fits={data.fits.slice(0, 4)} />}
    </Box>
  );
};

export default TeamSquad;
