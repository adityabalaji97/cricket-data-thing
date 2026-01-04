import React from 'react';
import { Box, Typography } from '@mui/material';
import { colors, spacing, typography, zIndex, transitions, borderRadius } from '../../theme/designSystem';

const MobileStickyHeader = ({
  title,
  stats = [],
  action = null,
  enableCollapse = false,
  collapseOffset = 80,
}) => {
  const [collapsed, setCollapsed] = React.useState(false);

  React.useEffect(() => {
    if (!enableCollapse) {
      setCollapsed(false);
      return undefined;
    }

    const handleScroll = () => {
      setCollapsed(window.scrollY > collapseOffset);
    };

    handleScroll();
    window.addEventListener('scroll', handleScroll, { passive: true });

    return () => window.removeEventListener('scroll', handleScroll);
  }, [collapseOffset, enableCollapse]);

  return (
    <Box
      sx={{
        position: 'sticky',
        top: 0,
        zIndex: zIndex.sticky,
        backgroundColor: colors.neutral[0],
        borderBottom: `1px solid ${colors.neutral[200]}`,
        transition: `all ${transitions.base}`,
        px: `${spacing.base}px`,
        py: collapsed ? `${spacing.sm}px` : `${spacing.base}px`,
        boxShadow: collapsed ? '0 2px 6px rgba(0, 0, 0, 0.06)' : 'none',
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Typography variant="h6" sx={{ fontWeight: typography.fontWeight.semibold }}>
          {title}
        </Typography>
        {action && <Box sx={{ display: 'flex', alignItems: 'center' }}>{action}</Box>}
      </Box>

      <Box
        sx={{
          display: collapsed ? 'none' : 'grid',
          gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
          gap: `${spacing.sm}px`,
          mt: `${spacing.sm}px`,
          transition: `all ${transitions.base}`,
        }}
      >
        {stats.map((stat) => (
          <Box
            key={stat.label}
            sx={{
              backgroundColor: colors.neutral[50],
              borderRadius: `${borderRadius.base}px`,
              px: `${spacing.sm}px`,
              py: `${spacing.xs}px`,
            }}
          >
            <Typography variant="caption" sx={{ color: colors.neutral[600], fontWeight: typography.fontWeight.medium }}>
              {stat.label}
            </Typography>
            <Typography variant="body1" sx={{ fontWeight: typography.fontWeight.semibold }}>
              {stat.value}
            </Typography>
            {stat.subLabel && (
              <Typography variant="caption" sx={{ color: colors.neutral[500] }}>
                {stat.subLabel}
              </Typography>
            )}
          </Box>
        ))}
      </Box>
    </Box>
  );
};

export default MobileStickyHeader;
