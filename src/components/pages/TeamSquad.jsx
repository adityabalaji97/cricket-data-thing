import React, { useEffect, useState } from 'react';
import { Box } from '@mui/material';
import config from '../../config';
import { colors } from '../../theme/hindsightDark';
import ProfileCard from '../playerProfile/cards/ProfileCard';
import { POST_VISUALS } from '../story/postVisuals';
import { Eyebrow } from '../pageKit/pageKit';

// The team page's Squad group (XI_BUILDER_PLAN.md X3): the IPL retention post's four squad cards, from the same build
// (GET /team-squad, services/squad_view.py), so the page and the post never disagree. IPL sides only; hidden otherwise.

const NAMES = { board: 'Squad', template: "Against the winners' template", value: 'Price v wins added', cases: 'Three calls' };
// What the copy calls a player: the surname, or the first name where the surname is shared by many (the retention
// posts' called(): "Arshdeep", not "Singh").
const COMMON = new Set(['Ahmed', 'Ahmad', 'Khan', 'Singh', 'Sharma', 'Kumar', 'Yadav', 'Patel', 'Pandya', 'Iyer']);
const surname = (n) => { const w = n.split(' '); return w.length > 1 && COMMON.has(w[w.length - 1]) ? w[0] : w[w.length - 1]; };

const dealLine = (d) => `${d.ins.map(surname).join(', ')} in, ${d.outs.map(surname).join(', ')} out`
  + (/awaiting/.test(d.source || '') ? ' · awaiting BCCI' : '');

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
          : c.sample;
        const payload = board ? { ...c.payload, note: null } : c.payload;
        return (
          <ProfileCard key={c.id} id={`squad-${c.id}`} title={NAMES[c.id] || c.kicker} player={team} note={note}>
            <Box sx={{ mx: -0.5 }}><Visual payload={payload} /></Box>
          </ProfileCard>
        );
      })}
    </Box>
  );
};

export default TeamSquad;
