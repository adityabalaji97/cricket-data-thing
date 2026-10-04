import { useEffect, useState } from 'react';

/**
 * Size of a story card's shareable core: 4:5, as wide as the screen allows once the progress bar
 * (top) and the action strip (bottom) have their room, so a screenshot cropped to the core is the
 * 1080x1350 feed format api/img.mjs uses. MATCH_PREVIEW_VIZ_PLAN.md, "Story shell".
 */
export const STORY_TOP = 56;     // progress segments + chapter line
export const STORY_BOTTOM = 72;  // action strip (outside the share crop)
export const STORY_GUTTER = 12;
export const STORY_MAX_WIDTH = 460;
export const GRID_CARD_WIDTH = 360;

export const coreSizeFor = (vw, vh) => {
  const byWidth = vw - STORY_GUTTER * 2;
  const byHeight = (vh - STORY_TOP - STORY_BOTTOM - STORY_GUTTER) * 0.8;
  const width = Math.max(240, Math.floor(Math.min(byWidth, byHeight, STORY_MAX_WIDTH)));
  return { width, height: Math.round(width * 1.25) };
};

export const useStoryCoreSize = () => {
  const read = () => coreSizeFor(window.innerWidth, window.innerHeight);
  const [size, setSize] = useState(read);
  useEffect(() => {
    const onResize = () => setSize(read());
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);
  return size;
};

// Short form of the credits every card carries (full wording lives in the info sheet and in
// analysis/hypotheses/credits.py; the 2015+ feed provider is still to be confirmed).
export const CARD_CREDITS = 'Data: Cricsheet, [feed TBC], Primer method';
export const CARD_BRAND = 'Hindsight · hindsightcricket.com';
