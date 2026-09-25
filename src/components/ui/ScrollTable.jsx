import React, { forwardRef, useCallback, useEffect, useRef, useState } from 'react';
import { Box, Paper } from '@mui/material';

/**
 * Drop-in replacement for MUI's TableContainer, for tables wider than a phone.
 *
 * TableContainer already scrolls sideways, but nothing tells you it does: columns simply stop at
 * the screen edge. This adds a fade on whichever edge has more to scroll (and removes it at the
 * ends), and can pin the first column so row labels stay visible while the numbers scroll.
 *
 *   <ScrollTable paper sx={{ mt: 2, maxHeight: 400 }}>   // was <TableContainer component={Paper} ...>
 *   <ScrollTable stickyFirstColumn>                       // player/team name stays put
 *
 * Margin keys in `sx` go on the outer box (so a Paper keeps its gap outside the border); every
 * other key, maxHeight included, goes on the scrolling element.
 */
const MARGIN_KEYS = new Set(['m', 'mt', 'mb', 'ml', 'mr', 'mx', 'my', 'margin', 'marginTop', 'marginBottom', 'marginLeft', 'marginRight']);

const splitSx = (sx = {}) => {
  const outer = {};
  const inner = {};
  if (typeof sx !== 'object' || Array.isArray(sx)) return { outer, inner: sx };
  Object.entries(sx).forEach(([key, value]) => {
    (MARGIN_KEYS.has(key) ? outer : inner)[key] = value;
  });
  return { outer, inner };
};

const fade = (side, visible, color) => ({
  position: 'absolute',
  top: 0,
  bottom: 0,
  [side]: 0,
  width: 28,
  pointerEvents: 'none',
  opacity: visible ? 1 : 0,
  transition: 'opacity 0.15s ease',
  background: `linear-gradient(to ${side === 'left' ? 'right' : 'left'}, ${color}, transparent)`,
  zIndex: 3,
});

const ScrollTable = forwardRef(function ScrollTable(
  { paper = false, stickyFirstColumn = false, sx, children, variant, elevation, ...rest },
  ref,
) {
  const scrollerRef = useRef(null);
  const [edges, setEdges] = useState({ left: false, right: false });

  const update = useCallback(() => {
    const el = scrollerRef.current;
    if (!el) return;
    const max = el.scrollWidth - el.clientWidth;
    setEdges((prev) => {
      const next = { left: el.scrollLeft > 2, right: el.scrollLeft < max - 2 };
      return prev.left === next.left && prev.right === next.right ? prev : next;
    });
  }, []);

  useEffect(() => {
    const el = scrollerRef.current;
    if (!el) return undefined;
    update();
    if (typeof ResizeObserver === 'undefined') return undefined;
    const observer = new ResizeObserver(update);
    observer.observe(el);
    if (el.firstElementChild) observer.observe(el.firstElementChild);
    return () => observer.disconnect();
  }, [update, children]);

  const setRefs = (node) => {
    scrollerRef.current = node;
    if (typeof ref === 'function') ref(node);
    else if (ref) ref.current = node;
  };

  const { outer, inner } = splitSx(sx);
  const Outer = paper ? Paper : Box;
  const outerProps = paper ? { variant, elevation } : {};

  return (
    <Outer {...outerProps} sx={{ position: 'relative', minWidth: 0, ...outer }}>
      <Box
        ref={setRefs}
        onScroll={update}
        {...rest}
        sx={{
          width: '100%',
          overflowX: 'auto',
          WebkitOverflowScrolling: 'touch',
          ...(stickyFirstColumn && {
            '& tbody td:first-of-type, & thead th:first-of-type': {
              position: 'sticky',
              left: 0,
              zIndex: 2,
              bgcolor: 'background.paper',
            },
            '& thead th:first-of-type': { zIndex: 4 },
          }),
          ...inner,
        }}
      >
        {children}
      </Box>
      <Box aria-hidden sx={(theme) => fade('left', edges.left && !stickyFirstColumn, theme.palette.background.paper)} />
      <Box aria-hidden sx={(theme) => fade('right', edges.right, theme.palette.background.paper)} />
    </Outer>
  );
});

export default ScrollTable;
