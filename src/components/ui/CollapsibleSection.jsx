import React, { useCallback, useEffect, useState } from 'react';
import { Box, ButtonBase, Collapse, Typography } from '@mui/material';
import ExpandMoreRoundedIcon from '@mui/icons-material/ExpandMoreRounded';
import { colors } from '../../theme/hindsightDark';
import { SECTION_SCROLL_MARGIN } from '../../theme/layout';

const OPEN_EVENT = 'hs:open-section';

/**
 * Open (and scroll to) a CollapsibleSection from anywhere: the sticky chip bar, an "At a glance"
 * card that links to its detail section, a #hash link.
 */
export const openSection = (id, { scroll = true } = {}) => {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent(OPEN_EVENT, { detail: { id, scroll } }));
};

/**
 * A page section that phones can fold away.
 *
 * The match preview and player profile were 7-11 sections of one long scroll, so the answer a
 * reader came for was several thumb-flicks down. Sections now open with a one-line takeaway in
 * the header ("Scores 31% faster vs spin") and only the ones that answer the page's question
 * start open.
 *
 * Children mount on first open and then stay mounted, so a section fetches only once it is read
 * and never refetches on re-open. `defaultOpen` sections mount immediately. The section also
 * opens when its id arrives as the URL hash or through openSection().
 */
const CollapsibleSection = ({
  id,
  title,
  takeaway,
  defaultOpen = false,
  actions,
  children,
  sx = {},
}) => {
  const [open, setOpen] = useState(() => {
    if (typeof window !== 'undefined' && id && window.location.hash === `#${id}`) return true;
    return defaultOpen;
  });
  const [mounted, setMounted] = useState(open);

  const reveal = useCallback((scroll) => {
    setOpen(true);
    setMounted(true);
    if (scroll && id) {
      // Wait a frame so the expanding content does not shift the scroll target.
      requestAnimationFrame(() => {
        const node = document.getElementById(id);
        if (node) node.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    }
  }, [id]);

  useEffect(() => {
    if (!id) return undefined;
    const onOpen = (event) => {
      if (event.detail?.id === id) reveal(event.detail.scroll !== false);
    };
    const onHash = () => {
      if (window.location.hash === `#${id}`) reveal(true);
    };
    window.addEventListener(OPEN_EVENT, onOpen);
    window.addEventListener('hashchange', onHash);
    return () => {
      window.removeEventListener(OPEN_EVENT, onOpen);
      window.removeEventListener('hashchange', onHash);
    };
  }, [id, reveal]);

  const toggle = () => {
    setOpen((prev) => !prev);
    setMounted(true);
  };

  const headerId = id ? `${id}-header` : undefined;
  const panelId = id ? `${id}-panel` : undefined;

  return (
    <Box
      id={id}
      component="section"
      sx={{
        scrollMarginTop: SECTION_SCROLL_MARGIN,
        borderTop: `1px solid ${colors.border}`,
        ...sx,
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <ButtonBase
          id={headerId}
          onClick={toggle}
          aria-expanded={open}
          aria-controls={panelId}
          sx={{
            flex: 1,
            minWidth: 0,
            minHeight: 56,
            py: 1.25,
            justifyContent: 'flex-start',
            textAlign: 'left',
            gap: 1,
            borderRadius: 1,
            '&:focus-visible': { outline: `2px solid ${colors.accent}`, outlineOffset: 2 },
          }}
        >
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography
              component="h2"
              sx={{ fontWeight: 700, fontSize: { xs: 17, md: 19 }, color: colors.textHi, lineHeight: 1.25 }}
            >
              {title}
            </Typography>
            {takeaway && (
              <Typography
                sx={{
                  mt: 0.25,
                  fontSize: 13,
                  color: colors.textLo,
                  lineHeight: 1.35,
                  // Folded: one line. Open: the full sentence.
                  ...(open ? {} : { whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }),
                }}
              >
                {takeaway}
              </Typography>
            )}
          </Box>
          <ExpandMoreRoundedIcon
            sx={{
              flexShrink: 0,
              color: colors.textLo,
              transition: 'transform 180ms ease',
              transform: open ? 'rotate(180deg)' : 'none',
            }}
          />
        </ButtonBase>
        {actions && open && <Box sx={{ flexShrink: 0 }}>{actions}</Box>}
      </Box>
      <Collapse in={open} timeout={180} unmountOnExit={false}>
        <Box id={panelId} role="region" aria-labelledby={headerId} sx={{ pb: 2.5 }}>
          {mounted ? children : null}
        </Box>
      </Collapse>
    </Box>
  );
};

export default CollapsibleSection;
