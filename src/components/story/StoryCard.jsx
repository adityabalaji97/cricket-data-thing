import React, { useLayoutEffect, useRef, useState } from 'react';
import { Box, IconButton, Typography } from '@mui/material';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import DetailSheet from '../ui/DetailSheet';
import { colors, fonts } from '../../theme/hindsightDark';
import { CARD_BRAND, CARD_CREDITS } from './storyLayout';
import { track } from '../../utils/analytics';

/**
 * One story card's shareable core (4:5): title (the takeaway) with an info button, at most one
 * help line ("Higher is better"), the chart, and two footer lines that always stay on the card:
 * sample + context (CARTA Complete/Accurate) and brand + credits. Everything else about the chart
 * lives in the info sheet.
 *
 * The chart area never scrolls: content that does not fit is a bug in that card, so it is
 * flagged in development (data-overflow) for the UI sweep to catch.
 */
// Events from a chart's own controls, or from sheets it opens (portals: React bubbles them through
// this tree although they sit elsewhere in the DOM), stay with the chart. Otherwise a tap there
// would also open the card (grid) or count as a swipe (story).
const keepInChart = (e) => {
  const fromPortal = !e.currentTarget.contains(e.target);
  const fromControl = e.target.closest && e.target.closest('button, a, [role="button"], input, select');
  if (fromPortal || fromControl) e.stopPropagation();
};

// exportMode (Instagram slides, src/components/ig/IgSlide.jsx): the card fills the image, no info button; `corner`
// (e.g. "2 / 7") takes the button's place.
const StoryCard = ({ card, width, height, exportMode = false, corner = null }) => {
  const [infoOpen, setInfoOpen] = useState(false);
  const [overflow, setOverflow] = useState(false);
  const chartRef = useRef(null);

  useLayoutEffect(() => {
    const el = chartRef.current;
    if (!el) return;
    const over = el.scrollHeight > el.clientHeight + 1 || el.scrollWidth > el.clientWidth + 1;
    setOverflow(over);
    if (over && process.env.NODE_ENV !== 'production') {
      // eslint-disable-next-line no-console
      console.warn(`Story card "${card.id}" does not fit its core`);
    }
  }, [card, width, height]);

  return (
    <Box
      data-story-card={card.id}
      data-overflow={overflow ? 'true' : undefined}
      sx={{
        width,
        height,
        display: 'flex',
        flexDirection: 'column',
        bgcolor: exportMode ? colors.bg : colors.surface1,
        border: exportMode ? 'none' : `1px solid ${colors.border}`,
        borderRadius: exportMode ? 0 : '20px',
        px: 2,
        pt: 1.75,
        pb: 1.25,
        boxSizing: 'border-box',
        overflow: 'hidden',
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
        <Typography
          component="h2"
          sx={{
            flex: 1,
            minWidth: 0,
            fontFamily: fonts.display,
            fontWeight: 700,
            fontSize: width < 330 ? 20 : 22,
            lineHeight: 1.15,
            color: colors.textHi,
            display: '-webkit-box',
            WebkitLineClamp: 3,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {card.title}
        </Typography>
        {corner && (
          <Typography sx={{ fontSize: 12, color: colors.textLo, mt: 0.5, whiteSpace: 'nowrap' }}>{corner}</Typography>
        )}
        {card.info && !exportMode && (
          <IconButton
            aria-label={`About this chart: ${card.title}`}
            onClick={(e) => { e.stopPropagation(); setInfoOpen(true); track('card_info', { card: card.id }); }}
            data-story-noswipe
            sx={{ width: 36, height: 36, mt: -0.5, mr: -1, color: colors.textLo }}
          >
            <InfoOutlinedIcon fontSize="small" />
          </IconButton>
        )}
      </Box>
      {card.help && (
        <Typography sx={{ fontSize: 13, color: colors.textLo, mt: 0.5 }}>{card.help}</Typography>
      )}

      <Box
        ref={chartRef}
        onClick={keepInChart}
        onPointerDown={keepInChart}
        onPointerUp={keepInChart}
        sx={{ flex: 1, minHeight: 0, mt: 1.25, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}
      >
        {card.render()}
      </Box>

      <Box sx={{ mt: 1, pt: 1, borderTop: `1px solid ${colors.border}` }}>
        <Typography sx={{ fontSize: 12, color: colors.textMed, lineHeight: 1.35 }}>
          {card.sample}
          {card.smallSample && (
            <Box component="span" sx={{ color: colors.gold, fontWeight: 600 }}> · small sample</Box>
          )}
        </Typography>
        <Typography sx={{ fontSize: 11, color: colors.textFaint, lineHeight: 1.35, mt: 0.25 }}>
          {CARD_BRAND} · {CARD_CREDITS}
        </Typography>
      </Box>

      {card.info && !exportMode && (
        // The sheet is a portal, but React still bubbles its events through this tree: stop them
        // here so a tap in the sheet never opens the card (grid) or counts as a swipe (story).
        <Box
          component="span"
          onClick={(e) => e.stopPropagation()}
          onPointerDown={(e) => e.stopPropagation()}
          onPointerUp={(e) => e.stopPropagation()}
          onKeyDown={(e) => e.stopPropagation()}
        >
        <DetailSheet open={infoOpen} onClose={() => setInfoOpen(false)} title={card.title} subtitle={card.sample}>
          <Box sx={{ color: colors.textMed, fontSize: 14, lineHeight: 1.5 }}>{card.info}</Box>
          <Typography sx={{ mt: 2, fontSize: 12, color: colors.textFaint, lineHeight: 1.5 }}>
            Data: Hindsight (hindsightcricket.com). Ball-by-ball data before 2015: Cricsheet (ODC-By 1.0).
            2015+ ball-by-ball, line, length and shot: provider to be confirmed. Impact, RAA, WAA, WPA and
            leverage are computed ball by ball using Himanish Ganjoo&apos;s T20 Primer method.
          </Typography>
        </DetailSheet>
        </Box>
      )}
    </Box>
  );
};

export default StoryCard;
