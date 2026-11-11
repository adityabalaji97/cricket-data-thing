import React, { useEffect, useState } from 'react';
import { Box } from '@mui/material';
import { colors, fonts } from '../../../theme/hindsightDark';
import { getTeamColor, readableOnDark } from '../../../utils/teamColors';
import ProfileCard from './ProfileCard';
import config from '../../../config';

// His IPL auctions (GET /player/{name}/auctions, migration 038): one row a year, the price as a bar in the team's
// colour, what happened in words. Hidden when he has none. 2018 on is complete; before that, the top 20 lots a year.

const mono = { fontFamily: fonts.mono, fontVariantNumeric: 'tabular-nums' };
const WHAT = { sold: 'Bought', retained: 'Retained', rtm: 'Right to match', traded: 'Traded', drafted: 'Drafted',
  replacement: 'Replacement', unsold: 'Unsold' };
const money = (lakh) => (lakh == null ? null : lakh >= 100 ? `₹${(lakh / 100).toFixed(2).replace(/\.00$/, '').replace(/(\.\d)0$/, '$1')} cr` : `₹${Math.round(lakh)} L`);

const AuctionCard = ({ player }) => {
  const [lots, setLots] = useState(null);
  useEffect(() => {
    let cancelled = false;
    fetch(`${config.API_URL}/player/${encodeURIComponent(player)}/auctions`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (!cancelled) setLots(d?.lots || []); })
      .catch(() => { if (!cancelled) setLots([]); });
    return () => { cancelled = true; };
  }, [player]);
  if (!lots?.length) return null;
  const max = Math.max(...lots.map((l) => l.price_lakh || 0), 1);
  const bids = lots.find((l) => l.status === 'sold' && l.bids > 1);
  return (
    <ProfileCard id="auctions" title="IPL auctions" player={player}
      note={bids ? `Price per season · ${bids.year}: ${bids.bids} bids` : 'Price per season'}>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.9 }}>
        {lots.map((l) => {
          const colour = readableOnDark(getTeamColor(l.team_name) || colors.accent);
          const sold = l.status !== 'unsold' && l.price_lakh != null;
          return (
            <Box key={l.year} sx={{ display: 'grid', gridTemplateColumns: '40px 1fr auto', alignItems: 'center', gap: 1 }}>
              <Box sx={{ ...mono, fontSize: 13, color: colors.textMed }}>{l.year}</Box>
              <Box sx={{ minWidth: 0, lineHeight: 1.15 }}>
                <Box sx={{ height: 10, bgcolor: 'rgba(255,255,255,0.04)', borderRadius: '4px', overflow: 'hidden' }}>
                  {sold && <Box sx={{ height: '100%', width: `${Math.max(2, (100 * l.price_lakh) / max)}%`, bgcolor: colour, borderRadius: '4px' }} />}
                </Box>
                <Box sx={{ fontSize: 11, color: colors.textLo, whiteSpace: 'nowrap', mt: 0.4, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {[WHAT[l.status] || l.status, l.team && l.status !== 'unsold' ? `by ${l.team}` : null,
                    l.status === 'unsold' && l.base_lakh ? `base ${money(l.base_lakh)}` : null].filter(Boolean).join(' ')}
                </Box>
              </Box>
              <Box sx={{ ...mono, fontSize: 13, textAlign: 'right', whiteSpace: 'nowrap', minWidth: 64, color: sold ? colors.textHi : colors.textLo }}>
                {sold ? money(l.price_lakh) : '–'}
              </Box>
            </Box>
          );
        })}
      </Box>
    </ProfileCard>
  );
};

export default AuctionCard;
