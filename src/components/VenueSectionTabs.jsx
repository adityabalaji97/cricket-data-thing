import React, { useRef, useEffect } from 'react';
import { Box, Chip } from '@mui/material';

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
      top: 0,
      zIndex: 1100,
      bgcolor: 'rgba(255,255,255,0.95)',
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
