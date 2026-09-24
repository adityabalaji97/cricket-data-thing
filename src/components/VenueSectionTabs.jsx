import React, { useRef, useEffect } from 'react';
import { Box, Chip } from '@mui/material';
import { STICKY_BELOW_HEADER } from '../theme/layout';

const VenueSectionTabs = ({ sections, activeSectionId, onSectionSelect }) => {
  const chipRefs = useRef([]);

  useEffect(() => {
    const activeIndex = sections.findIndex(s => s.id === activeSectionId);
    if (chipRefs.current[activeIndex]) {
      chipRefs.current[activeIndex].scrollIntoView({
        behavior: 'smooth',
        inline: 'center',
        block: 'nearest',
      });
    }
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
