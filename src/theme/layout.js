/**
 * Shared layout offsets for sticky chrome.
 *
 * Below `md` the app header is sticky (App.js, COMPACT_HEADER_HEIGHT tall), so the sticky
 * section-chip bars (VenueSectionTabs) must sit under it rather than at top: 0, and a section
 * scrolled into view must clear both bars. At md+ the header scrolls away and only the chip bar
 * sticks. Keep these in step with App.js and VenueSectionTabs.
 */
export const COMPACT_HEADER_HEIGHT = 52;

/** `top` for sticky bars that sit under the app header. */
export const STICKY_BELOW_HEADER = { xs: `${COMPACT_HEADER_HEIGHT}px`, md: 0 };

/** `scrollMarginTop` for sections reached from a sticky chip bar. */
export const SECTION_SCROLL_MARGIN = { xs: `${COMPACT_HEADER_HEIGHT + 56}px`, md: '56px' };
