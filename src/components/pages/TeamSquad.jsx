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
const surname = (n) => n.split(' ').slice(-1)[0];

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
        const trades = c.id === 'board' && data.deals?.length ? data.deals.map(dealLine).join(' · ') : null;
        return (
          <ProfileCard key={c.id} id={`squad-${c.id}`} title={NAMES[c.id] || c.kicker} player={team}
            note={trades || c.sample}>
            <Box sx={{ mx: -0.5 }}><Visual payload={c.payload} /></Box>
          </ProfileCard>
        );
      })}
    </Box>
  );
};

export default TeamSquad;
