import React from 'react';
import { Box, Tooltip } from '@mui/material';
import { colors, fonts } from '../../../theme/hindsightDark';
import { getTeamAbbr } from '../../../utils/teamAbbreviations';

const BAND = 2; // runs above par either side of zero that count as level

const tone = (raa) => {
  if (raa === null || raa === undefined) return 'none';
  if (raa > BAND) return 'up';
  if (raa < -BAND) return 'down';
  return 'flat';
};

const STYLE = {
  up: { bg: 'rgba(182,242,74,0.13)', border: 'rgba(182,242,74,0.45)', glyph: '▲', glyphColour: colors.accent },
  down: { bg: 'rgba(229,72,77,0.16)', border: 'rgba(229,72,77,0.5)', glyph: '▼', glyphColour: '#f87171' },
  flat: { bg: colors.surface1, border: colors.borderStrong, glyph: '●', glyphColour: colors.textFaint },
  none: { bg: 'transparent', border: colors.borderStrong, glyph: ' ', glyphColour: colors.textFaint },
};

const short = (team) => {
  const a = getTeamAbbr(team);
  return a && a !== team ? a : (team || '?').replace(/\s*\(.*\)$/, '').slice(0, 4).toUpperCase();
};

// The last 8 games, coloured by runs above par (bat and ball together), never by wickets alone: a 0/16 in four overs
// is a good spell. Games with no par (The Hundred, ODIs) stay neutral with a dashed edge.
const FormChips = ({ games }) => {
  if (!games || !games.length) return null;
  return (
    <Box sx={{ display: 'grid', gridTemplateColumns: `repeat(${games.length}, minmax(0, 1fr))`, gap: '4px' }}>
      {games.map((g) => {
        const t = tone(g.raa);
        const st = STYLE[t];
        const parts = [];
        if (g.bowl) parts.push(`Bowling ${g.bowl.wickets}/${g.bowl.runs} (${g.bowl.balls} balls)`);
        if (g.bat) parts.push(`Batting ${g.bat.runs}${g.bat.wickets ? '' : '*'} off ${g.bat.balls}`);
        const par = g.raa === null || g.raa === undefined
          ? 'No par for this match'
          : `${g.raa > 0 ? '+' : ''}${g.raa.toFixed(1)} runs above par`;
        return (
          <Tooltip key={g.match_id} enterTouchDelay={0} placement="top"
            title={`v ${g.opponent} · ${g.date} · ${g.competition}. ${parts.join('; ')}. ${par}.`}>
            <Box tabIndex={0} sx={{
              borderRadius: '8px', py: '3px', display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: 0,
              bgcolor: st.bg, border: `1px ${t === 'none' ? 'dashed' : 'solid'} ${st.border}`,
            }}>
              <Box component="span" sx={{ fontSize: 8, lineHeight: 1, height: 9, color: st.glyphColour }}>{st.glyph}</Box>
              {g.bowl && (
                <Box component="span" sx={{ fontFamily: fonts.display, fontWeight: 600, fontSize: 12.5, lineHeight: 1.15, whiteSpace: 'nowrap' }}>
                  {g.bowl.wickets}/{g.bowl.runs}
                </Box>
              )}
              {g.bat && (
                <Box component="span" sx={{ fontFamily: fonts.display, fontWeight: g.bowl ? 500 : 600, fontSize: g.bowl ? 11 : 12.5, lineHeight: 1.15, color: g.bowl ? colors.textMed : colors.textHi, whiteSpace: 'nowrap' }}>
                  {g.bat.runs}{g.bat.wickets ? '' : '*'}
                  <Box component="span" sx={{ color: colors.textLo, fontWeight: 500 }}> ({g.bat.balls})</Box>
                </Box>
              )}
              <Box component="span" sx={{ fontFamily: fonts.mono, fontSize: 8.5, color: colors.textLo, mt: '1px' }}>{short(g.opponent)}</Box>
            </Box>
          </Tooltip>
        );
      })}
    </Box>
  );
};

export default FormChips;
