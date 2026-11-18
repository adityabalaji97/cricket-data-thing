import React from 'react';
import { Box } from '@mui/material';
import { colors } from '../../../../theme/hindsightDark';
import { easeOut, progress, teamTone, u } from '../motion';
import { At, Count, Scope, enter, pop, splitName, type } from './common';

/**
 * A. Hero count-up (M1 decision 9): the player's name at full size on frame 0, the number counting up within 0.8s, a
 * second name and number entering by 1.5s with its tag, the scope line. Frame 0 is never empty.
 * data: { name, value, format, unit, from?, gloss?, second?: { name, value, format, unit, tag, at? }, scope? }
 */
const HeroScene = ({ scene, t, tone }) => {
  const d = scene.data || {};
  const s0 = scene.start;
  const { first, last } = splitName(d.name);
  const settle = easeOut(progress(t, s0, 0.6));
  const sec = d.second;
  const secAt = sec ? (sec.at ?? s0 + 1.4) : null;
  const secTone = sec && sec.team ? teamTone(sec.team) : tone;
  return (
    <>
      <At x={64} y={480} w={900} sx={{ transform: `translateY(${u(5 * Math.sin(t * 1.3))}px)${settle >= 1 ? '' : ` scale(${1.04 - 0.04 * settle})`}`, transformOrigin: 'left top' }}>
        {first && <Box sx={{ ...type.display(56, 600), color: colors.textMed }}>{first}</Box>}
        <Box sx={{ ...type.display(last.length > 9 ? 170 : 220), whiteSpace: 'nowrap' }}>{last}</Box>
      </At>
      <At x={64} y={760} w={876} sx={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
        <Box sx={{ ...type.mono(190), color: d.value < 0 ? colors.red : tone.light, lineHeight: 1 }}>
          <Count value={d.value} from={d.from ?? 0} format={d.format || 'signed2'} t={t} a={s0} dur={0.8} />
        </Box>
        {d.unit && <Box sx={{ ...type.display(84), color: colors.textHi }}>{d.unit}</Box>}
      </At>
      {d.gloss && (
        <At x={64} y={970} w={876} sx={{ ...type.mono(34, 500), color: colors.textLo, ...enter(t, s0 + 0.9, { dy: 30 }) }}>{d.gloss}</At>
      )}
      {sec && (
        <>
          <At x={64} y={1050} w={876} sx={{ ...enter(t, secAt, { dy: 70 }) }}>
            <Box sx={{ ...type.display(String(sec.name).length > 14 ? 96 : 110), whiteSpace: 'nowrap' }}>{sec.name}</Box>
          </At>
          <At x={64} y={1160} w={876} sx={{ display: 'flex', alignItems: 'baseline', gap: '10px', ...enter(t, secAt + 0.1, { dy: 50 }) }}>
            <Box sx={{ ...type.mono(130), color: sec.value < 0 ? colors.red : secTone.light, lineHeight: 1 }}>
              <Count value={sec.value} format={sec.format || d.format || 'signed2'} t={t} a={secAt + 0.1} dur={0.8} />
            </Box>
            {sec.unit && <Box sx={{ ...type.display(60) }}>{sec.unit}</Box>}
          </At>
          {sec.tag && (
            <At x={64} y={1310} sx={{ px: '6px', py: '3px', borderRadius: '4px', bgcolor: colors.gold, color: colors.bg, ...type.display(40), ...pop(t, secAt + 0.6) }}>
              {sec.tag}
            </At>
          )}
        </>
      )}
      {d.scope && <Scope y={1400} sx={enter(t, s0 + 0.4, { dy: 0 })}>{d.scope}</Scope>}
    </>
  );
};

export default HeroScene;
