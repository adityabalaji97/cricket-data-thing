/**
 * The desktop site menu: an "Explore" button and a right-hand drawer listing every page, grouped
 * as the mobile "More" sheet is (Main / Explore / Compare / Play), from the one NAV_ITEMS list.
 *
 * Replaces the desktop tab strip, which had outgrown the width and scrolled sideways, and the
 * landing page's separate curated drawer, so there is one menu with one set of links.
 */
import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Box, Button, IconButton, Typography } from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import CloseIcon from '@mui/icons-material/Close';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import { NAV_ITEMS, PRIMARY_NAV_PATHS, MAIN_MENU_EXTRA, MORE_NAV_GROUPS, MORE_EXTRA_LINKS } from '../../navItems';
import { useFormat } from '../../context/FormatContext';
import { colors, fonts } from '../../theme/hindsightDark';

const GROUPS = [{ key: 'main', label: 'Main' }, ...MORE_NAV_GROUPS];

const MAIN_PATHS = [...PRIMARY_NAV_PATHS, ...MAIN_MENU_EXTRA];
const groupFor = (item) => (MAIN_PATHS.includes(item.path) ? 'main' : item.group);

const menuItems = [
  // Main in the bottom-bar order (then Make a Graphic, next to Query Builder), then everything else.
  ...MAIN_PATHS.map((path) => NAV_ITEMS.find((item) => item.path === path)).filter(Boolean),
  ...NAV_ITEMS.filter((item) => !MAIN_PATHS.includes(item.path)),
  ...MORE_EXTRA_LINKS.filter((item) => item.group),
];

export const ExploreButton = ({ onClick, compact = false }) => (
  <Button
    type="button"
    onClick={onClick}
    startIcon={<MenuIcon />}
    aria-label="Open the site menu"
    sx={{
      minWidth: compact ? 42 : 116,
      width: compact ? 42 : 'auto',
      height: 42,
      px: compact ? 0 : 1.5,
      borderRadius: 2,
      color: colors.bg,
      bgcolor: colors.accent,
      fontFamily: fonts.mono,
      fontWeight: 700,
      fontSize: 11,
      letterSpacing: '0.12em',
      flexShrink: 0,
      '& .MuiButton-startIcon': { mr: compact ? 0 : 0.9 },
      '&:hover': { bgcolor: colors.accentHover },
    }}
  >
    {compact ? '' : 'Explore'}
  </Button>
);

const ExploreMenu = ({ open, onClose }) => {
  const { pathname } = useLocation();
  const { active } = useFormat();
  const isDefaultFormat = !active || active.slug === 'mens-t20';

  return (
    <>
      <Box
        onClick={onClose}
        sx={{
          position: 'fixed',
          inset: 0,
          zIndex: 1300,
          bgcolor: 'rgba(0,0,0,0.45)',
          opacity: open ? 1 : 0,
          pointerEvents: open ? 'auto' : 'none',
          transition: 'opacity 0.28s cubic-bezier(0.22,1,0.36,1)',
        }}
      />
      <Box
        component="nav"
        aria-label="Site menu"
        aria-hidden={!open}
        sx={{
          position: 'fixed',
          top: 0,
          right: 0,
          bottom: 0,
          width: { xs: '86%', sm: 380 },
          zIndex: 1301,
          bgcolor: colors.surface1,
          borderLeft: `1px solid ${colors.borderStrong}`,
          p: 2,
          overflowY: 'auto',
          transform: open ? 'translateX(0)' : 'translateX(102%)',
          visibility: open ? 'visible' : 'hidden',
          pointerEvents: open ? 'auto' : 'none',
          transition: open
            ? 'transform 0.28s cubic-bezier(0.22,1,0.36,1)'
            : 'transform 0.28s cubic-bezier(0.22,1,0.36,1), visibility 0s linear 0.28s',
          boxShadow: '0 0 60px rgba(0,0,0,0.5)',
        }}
      >
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
          <Box>
            <Typography sx={{ fontFamily: fonts.mono, fontSize: 11, letterSpacing: '0.12em', textTransform: 'uppercase', color: colors.accent }}>
              Explore
            </Typography>
            <Typography sx={{ color: colors.textHi, fontFamily: fonts.display, fontWeight: 700, fontSize: 22 }}>
              Hindsight tools
            </Typography>
          </Box>
          <IconButton aria-label="Close the site menu" onClick={onClose} sx={{ color: colors.textHi }}>
            <CloseIcon />
          </IconButton>
        </Box>

        {GROUPS.map((group) => {
          const items = menuItems.filter((item) => groupFor(item) === group.key);
          if (!items.length) return null;
          return (
            <Box key={group.key} sx={{ mt: 1.5 }}>
              <Typography sx={{ fontFamily: fonts.mono, fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase', color: colors.textLo, mb: 0.75 }}>
                {group.label}
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                {items.map((item) => {
                  const current = pathname === item.path;
                  return (
                    <Box
                      key={item.path}
                      component={Link}
                      to={item.path}
                      onClick={onClose}
                      aria-current={current ? 'page' : undefined}
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 1,
                        px: 1.25,
                        py: 1,
                        borderRadius: 2,
                        textDecoration: 'none',
                        color: current ? colors.accent : colors.textHi,
                        border: `1px solid ${current ? colors.accent : colors.border}`,
                        bgcolor: current ? colors.accentSoft : colors.surface2,
                        '&:hover': { borderColor: colors.borderStrong, bgcolor: colors.surface3 },
                      }}
                    >
                      <Box sx={{ flex: 1, minWidth: 0 }}>
                        <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 15.5, color: 'inherit' }}>
                          {item.label}
                        </Typography>
                        {item.t20Only && !isDefaultFormat && (
                          <Typography sx={{ fontSize: 11.5, color: colors.textLo }}>Men's T20</Typography>
                        )}
                      </Box>
                      <ChevronRightIcon sx={{ color: colors.textLo, fontSize: 18 }} />
                    </Box>
                  );
                })}
              </Box>
            </Box>
          );
        })}

        {MORE_EXTRA_LINKS.filter((item) => !item.group).map((item) => (
          <Box
            key={item.path}
            component={Link}
            to={item.path}
            onClick={onClose}
            sx={{ display: 'block', mt: 2, color: colors.textLo, fontSize: 13, textDecoration: 'none', '&:hover': { color: colors.textHi } }}
          >
            {item.label}
          </Box>
        ))}
      </Box>
    </>
  );
};

export default ExploreMenu;
