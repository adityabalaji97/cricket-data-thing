import React, { useRef, useEffect } from 'react';
import { Box, Chip } from '@mui/material';
import { STICKY_BELOW_HEADER } from '../theme/layout';

const VenueSectionTabs = ({ sections, activeSectionId, onSectionSelect }) => {
  const chipRefs = useRef([]);

  useEffect(() => {
    const activeIndex = sections.findIndex(s => s.id === activeSectionId);
    const chip = chipRefs.current[activeIndex];
    if (!chip) return;
    // Centre the chip in its own row, sideways only. scrollIntoView also scrolled the page down to the row
    // whenever it sat below the fold (the player profile's verdict screen put it there on every load).
    let row = chip.parentElement;
    while (row && row !== document.body && row.scrollWidth <= row.clientWidth) row = row.parentElement;
    if (!row || row === document.body) return;
    const c = chip.getBoundingClientRect();
    const r = row.getBoundingClientRect();
    row.scrollTo({ left: row.scrollLeft + (c.left - r.left) - (row.clientWidth - c.width) / 2, behavior: 'smooth' });
  }, [activeSectionId, sections]);

  return (
    <Box sx={{
      position: 'sticky',
      top: STICKY_BELOW_HEADER,
      // Just under the app header (appBar 1100) so the header stays on top when both stick.
      zIndex: 1090,
      bgcolor: 'rgba(10,12,17,0.92)',
      backdropFilter: 'blur(8px)',
      borderBottom: '1px solid',
      borderColor: 'divider',
      px: 1.5,
      py: 1,
      display: 'flex',
      overflowX: 'auto',
      gap: 0.75,
      WebkitOverflowScrolling: 'touch',
      '&::-webkit-scrollbar': { display: 'none' },
      scrollbarWidth: 'none',
    }}>
      {sections.map((section, i) => (
        <Chip
          key={section.id}
          ref={(el) => { chipRefs.current[i] = el; }}
          label={section.label}
          size="small"
          variant={section.id === activeSectionId ? 'filled' : 'outlined'}
          color={section.id === activeSectionId ? 'primary' : 'default'}
          onClick={() => onSectionSelect(section.id)}
          sx={{
            flexShrink: 0,
            fontWeight: 600,
            fontSize: '0.8rem',
            height: 32,
          }}
        />
      ))}
    </Box>
  );
};

export default VenueSectionTabs;
