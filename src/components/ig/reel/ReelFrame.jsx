import React from 'react';
import { Box } from '@mui/material';
import { colors, fonts } from '../../../theme/hindsightDark';
import { FRAME, PAGE, alpha, clamp, progress, teamTone, u } from './motion';

/** An absolutely placed box in canvas px. */
export const At = ({ x, y, w, h, sx, children, ...rest }) => (
  <Box sx={{ position: 'absolute', left: u(x), top: u(y), width: w == null ? undefined : u(w), height: h == null ? undefined : u(h), ...sx }} {...rest}>
    {children}
  </Box>
);

/**
 * The chapter bars: one segment a chapter, widths in proportion to their length, the current one filling in the
 * team's light tone; a new chapter's track brightens for 0.3s as it starts.
 */
const Chapters = ({ chapters, t, tone }) => {
  const C = FRAME.chapters;
  return (
    <At x={C.x} y={C.y} w={C.w} h={C.h} sx={{ display: 'flex', gap: `${u(C.gap)}px` }}>
      {chapters.map((c) => {
        const fill = clamp((t - c.start) / Math.max(0.01, c.end - c.start));
        const flash = t >= c.start && t < c.start + 0.3 ? 1 - progress(t, c.start, 0.3) : 0;
        return (
          <Box key={`${c.label}-${c.start}`} sx={{ position: 'relative', flex: c.end - c.start, height: '100%', borderRadius: `${u(3)}px`,
            overflow: 'hidden', bgcolor: alpha(colors.textHi, 0.1 + 0.15 * flash) }}>
            <Box sx={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: `${fill * 100}%`, bgcolor: c.team ? teamTone(c.team).light : tone.light }} />  {/* a chapter may be one team's: its segment in that team's colour (M8) */}
          </Box>
        );
      })}
    </At>
  );
};

/** The glow drifting behind everything, in the scene's colour (as the finished Reels). */
const Glow = ({ t, colour }) => (
  <Box sx={{ position: 'absolute', left: 0, top: 0, width: u(1500), height: u(1500), borderRadius: '50%', willChange: 'transform',
    background: `radial-gradient(circle, ${alpha(colour, 0.3)} 0%, ${alpha(colour, 0.09)} 40%, ${alpha(colour, 0)} 70%)`,
    // whole canvas pixels: a sub-pixel offset left the gradient's raster depending on the frame drawn before
    transform: `translate(${u(Math.round(-380 + 240 * Math.sin(t * 0.42) + 20 * t))}px, ${u(Math.round(-520 + 160 * Math.cos(t * 0.33)))}px)` }} />
);

/** ?guides=1: Instagram's overlays (red) and the frame's reading boxes (dashed), for the phone safe-area check. */
const Guides = () => (
  <>
    {FRAME.keepClear.map((k) => (
      <At key={k.name} x={k.x} y={k.y} w={k.w} h={k.h} sx={{ bgcolor: alpha(colors.red, 0.25), border: `1px dashed ${colors.red}`, boxSizing: 'border-box', zIndex: 50 }} />
    ))}
    {[FRAME.chapters, FRAME.kicker, FRAME.content, FRAME.caption].map((b) => (
      <At key={`${b.x}-${b.y}`} x={b.x} y={b.y} w={b.w} h={b.h} sx={{ border: `1px dashed ${colors.accent}`, boxSizing: 'border-box', zIndex: 50 }} />
    ))}
  </>
);

/**
 * The frame every scene sits in: background, glow, the team stripe, the chapter bars, the scenes, the caption line.
 * No wordmark, no site name, no slide counter (decision 8): the one brand mention is the closing scene's credit.
 */
const ReelFrame = ({ t, tone, glow, chapters, guides, children, caption }) => (
  <Box sx={{ position: 'relative', width: PAGE.w, height: PAGE.h, overflow: 'hidden', bgcolor: colors.bg, color: colors.textHi, fontFamily: fonts.body }}>
    <Glow t={t} colour={glow} />
    <At x={FRAME.stripe.x} y={0} w={FRAME.stripe.w} h={1920} sx={{ bgcolor: glow }} />
    {chapters && chapters.length > 0 && <Chapters chapters={chapters} t={t} tone={tone} />}
    {children}
    {caption}
    {guides && <Guides />}
  </Box>
);

export default ReelFrame;
