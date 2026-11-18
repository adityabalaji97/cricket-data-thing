import React from 'react';
import { Box } from '@mui/material';
import { colors, fonts } from '../../../theme/hindsightDark';
import { FRAME, activeCaption, u } from './motion';
import { At } from './ReelFrame';

/** The caption line for t: one line, centred in the caption band, the spoken word in the lit colour (gold by default). */
const Captions = ({ captions, scenes, t, litColour = colors.gold }) => {
  const line = activeCaption(captions, t, scenes);
  const C = FRAME.caption;
  return (
    <At x={C.x} y={C.y} w={C.w} h={C.h} sx={{ textAlign: 'center', whiteSpace: 'nowrap', fontFamily: fonts.body, fontWeight: 700,
      fontSize: u(58), lineHeight: `${u(80)}px`, color: colors.textHi }} data-caption>
      {line && line.words.map((w, i) => (
        // eslint-disable-next-line react/no-array-index-key
        <Box component="span" key={i} sx={{ color: w.on ? litColour : colors.textHi }}>{i ? ' ' : ''}{w.w}</Box>
      ))}
    </At>
  );
};

export default Captions;
