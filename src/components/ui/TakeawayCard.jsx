import React from 'react';
import { Box, ButtonBase, Typography } from '@mui/material';
import { colors, fonts } from '../../theme/hindsightDark';

const deltaColor = (tone) => {
  if (tone === 'good') return '#0ca30c';
  if (tone === 'bad') return '#e66767';
  return colors.textLo;
};

/**
 * One headline number and what it means. The unit of the "What to expect" and "At a glance"
 * strips.
 *
 *   label     what is measured           "Par score"
 *   value     the number                 "178"
 *   unit      small suffix               "runs"
 *   delta     comparison, already worded "+12 vs venue avg"; deltaTone good | bad | neutral
 *             (a delta is always words + sign, never colour alone)
 *   caption   the takeaway sentence      "Chasing sides have won 6 of the last 8"
 *   footnote  sample / context           "41 matches since 2021"
 *   children  an optional mini chart, drawn between the value and the caption
 *
 * With `onClick` the card is a button (e.g. opens the detail section).
 */
const TakeawayCard = ({
  label,
  value,
  unit,
  delta,
  deltaTone = 'neutral',
  caption,
  footnote,
  highlight = false,
  onClick,
  children,
  sx = {},
}) => {
  const content = (
    <Box sx={{ width: '100%', textAlign: 'left', display: 'flex', flexDirection: 'column', gap: 0.5 }}>
      <Typography
        sx={{
          fontFamily: fonts.mono,
          fontSize: 11,
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
          color: colors.textLo,
        }}
      >
        {label}
      </Typography>
      <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 0.75, flexWrap: 'wrap' }}>
        <Typography
          sx={{
            fontFamily: fonts.display,
            fontWeight: 700,
            fontSize: 30,
            lineHeight: 1.05,
            color: highlight ? colors.accent : colors.textHi,
          }}
        >
          {value ?? '–'}
        </Typography>
        {unit && <Typography sx={{ fontSize: 13, color: colors.textLo }}>{unit}</Typography>}
      </Box>
      {delta && (
        <Typography sx={{ fontSize: 13, fontWeight: 600, color: deltaColor(deltaTone) }}>{delta}</Typography>
      )}
      {children && <Box sx={{ my: 0.5 }}>{children}</Box>}
      {caption && (
        <Typography sx={{ fontSize: 13, color: colors.textMed, lineHeight: 1.35 }}>{caption}</Typography>
      )}
      {footnote && (
        <Typography sx={{ fontSize: 12, color: colors.textFaint, mt: 'auto', pt: 0.5 }}>{footnote}</Typography>
      )}
    </Box>
  );

  const frame = {
    bgcolor: colors.surface1,
    border: `1px solid ${highlight ? 'rgba(182,242,74,0.35)' : colors.border}`,
    borderRadius: 3,
    p: 1.75,
    height: '100%',
    alignItems: 'stretch',
    ...sx,
  };

  if (onClick) {
    return (
      <ButtonBase
        onClick={onClick}
        sx={{ ...frame, display: 'flex', '&:focus-visible': { outline: `2px solid ${colors.accent}` } }}
      >
        {content}
      </ButtonBase>
    );
  }
  return <Box sx={{ ...frame, display: 'flex' }}>{content}</Box>;
};

/**
 * A row of TakeawayCards: swipes horizontally on phones (each card ~78% wide, so the next one
 * peeks in and signals there is more), wraps into a grid on wider screens.
 */
export const TakeawayStrip = ({ children, columns = 4, sx = {} }) => (
  <Box
    sx={{
      display: 'grid',
      gridAutoFlow: { xs: 'column', md: 'row' },
      gridAutoColumns: { xs: '78%', sm: '44%' },
      gridTemplateColumns: { md: `repeat(${columns}, minmax(0, 1fr))` },
      gap: 1.25,
      overflowX: { xs: 'auto', md: 'visible' },
      scrollSnapType: { xs: 'x mandatory', md: 'none' },
      '& > *': { scrollSnapAlign: 'start' },
      pb: { xs: 0.5, md: 0 },
      '&::-webkit-scrollbar': { display: 'none' },
      scrollbarWidth: 'none',
      ...sx,
    }}
  >
    {children}
  </Box>
);

export default TakeawayCard;
