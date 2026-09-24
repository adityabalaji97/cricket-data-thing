import React, { useEffect, useRef, useState } from 'react';
import { Box } from '@mui/material';

/**
 * Mounts its children only once they come near the viewport.
 *
 * The long pages (player profile, match preview) render a dozen sections that each fetch on
 * mount, so a single page load fired ~15 heavy requests at once. With a handful of DB
 * connections behind the API, most of them queued until Heroku's 30s router timeout and the
 * sections rendered "Failed to fetch". Deferring below-the-fold sections spreads that load out
 * to what the reader actually scrolls to.
 *
 * Once mounted, children stay mounted, so scrolling back up never refetches.
 *
 * `eager` mounts immediately (above-the-fold sections). `placeholderHeight` reserves space so
 * the page does not collapse and jump while sections below are still unmounted.
 */
const LazySection = ({ children, eager = false, rootMargin = '600px 0px', placeholderHeight = 320 }) => {
  const [visible, setVisible] = useState(eager);
  const ref = useRef(null);

  useEffect(() => {
    if (visible) return undefined;
    const node = ref.current;
    // No IntersectionObserver (very old browsers, some test envs): just render.
    if (!node || typeof IntersectionObserver === 'undefined') {
      setVisible(true);
      return undefined;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [visible, rootMargin]);

  if (visible) return children;
  return <Box ref={ref} sx={{ minHeight: placeholderHeight }} aria-busy="true" />;
};

export default LazySection;
