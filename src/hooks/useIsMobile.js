import { useMediaQuery, useTheme } from '@mui/material';

/**
 * The app's one breakpoint answer.
 *
 * Components used to decide "mobile" three ways: an `isMobile` prop threaded from App.js (which
 * several charts never received, so they rendered their desktop layout on phones), their own
 * useMediaQuery(down('sm')), or down('md'). Call this instead.
 *
 * - isMobile:  below `sm` (600px) — phones. Chart-level compaction (ticks, margins, columns).
 * - isCompact: below `md` (900px) — phones and portrait tablets. Page-level layout (single
 *   column, chip nav instead of the side nav).
 *
 * `noSsr` reads the real width on the first render, so charts don't mount at desktop size and
 * then re-layout.
 */
const useIsMobile = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'), { noSsr: true });
  const isCompact = useMediaQuery(theme.breakpoints.down('md'), { noSsr: true });
  return { isMobile, isCompact };
};

export default useIsMobile;
