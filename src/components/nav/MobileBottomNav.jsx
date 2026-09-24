import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  BottomNavigation,
  BottomNavigationAction,
  Box,
  Divider,
  List,
  ListItemButton,
  ListItemText,
  Paper,
  SwipeableDrawer,
  Typography,
} from '@mui/material';
import HomeRoundedIcon from '@mui/icons-material/HomeRounded';
import SearchRoundedIcon from '@mui/icons-material/SearchRounded';
import StadiumRoundedIcon from '@mui/icons-material/StadiumRounded';
import BoltRoundedIcon from '@mui/icons-material/BoltRounded';
import MenuRoundedIcon from '@mui/icons-material/MenuRounded';
import {
  NAV_ITEMS,
  PRIMARY_NAV_PATHS,
  MORE_NAV_GROUPS,
  MORE_EXTRA_LINKS,
} from '../../navItems';
import { useFormat } from '../../context/FormatContext';
import { colors, fonts } from '../../theme/hindsightDark';

/** Height of the bar itself; the safe-area inset is added on top of this. */
export const MOBILE_NAV_HEIGHT = 60;

/** Spacer for page content so the fixed bar never covers the last row of a page. */
export const MobileNavSpacer = () => (
  <Box sx={{ height: `calc(${MOBILE_NAV_HEIGHT + 12}px + env(safe-area-inset-bottom, 0px))` }} />
);

const PRIMARY_ICONS = {
  '/': <HomeRoundedIcon />,
  '/search': <SearchRoundedIcon />,
  '/venue': <StadiumRoundedIcon />,
  '/query': <BoltRoundedIcon />,
};

const MORE_VALUE = '__more__';

/**
 * Phone navigation: a fixed bottom bar for the four most-used pages plus a "More" sheet that
 * holds everything else, grouped. Replaces the old hamburger popover, which listed all fifteen
 * pages in one light menu with no grouping or active state.
 */
const MobileBottomNav = () => {
  const location = useLocation();
  const { supportsT20OnlyPages } = useFormat();
  const [moreOpen, setMoreOpen] = useState(false);

  const primaryItems = PRIMARY_NAV_PATHS
    .map((path) => NAV_ITEMS.find((item) => item.path === path))
    .filter(Boolean);

  const path = location.pathname;
  const activeValue = PRIMARY_NAV_PATHS.includes(path) ? path : MORE_VALUE;

  const moreItems = [
    ...NAV_ITEMS.filter((item) => !PRIMARY_NAV_PATHS.includes(item.path)),
    ...MORE_EXTRA_LINKS,
  ];

  return (
    <>
      <Paper
        component="nav"
        aria-label="Main navigation"
        square
        sx={{
          position: 'fixed',
          left: 0,
          right: 0,
          bottom: 0,
          zIndex: (theme) => theme.zIndex.appBar,
          borderTop: `1px solid ${colors.borderStrong}`,
          pb: 'env(safe-area-inset-bottom, 0px)',
          bgcolor: colors.surface1,
        }}
      >
        <BottomNavigation value={activeValue} showLabels>
          {primaryItems.map((item) => (
            <BottomNavigationAction
              key={item.path}
              value={item.path}
              label={item.short || item.label}
              icon={PRIMARY_ICONS[item.path]}
              component={Link}
              to={item.path}
              onClick={() => setMoreOpen(false)}
            />
          ))}
          <BottomNavigationAction
            value={MORE_VALUE}
            label="More"
            icon={<MenuRoundedIcon />}
            onClick={() => setMoreOpen(true)}
          />
        </BottomNavigation>
      </Paper>

      <SwipeableDrawer
        anchor="bottom"
        open={moreOpen}
        onOpen={() => setMoreOpen(true)}
        onClose={() => setMoreOpen(false)}
        disableSwipeToOpen
        PaperProps={{
          sx: {
            borderTopLeftRadius: 20,
            borderTopRightRadius: 20,
            border: `1px solid ${colors.borderStrong}`,
            maxHeight: '85vh',
            pb: `calc(${MOBILE_NAV_HEIGHT}px + env(safe-area-inset-bottom, 0px))`,
          },
        }}
      >
        <Box sx={{ display: 'flex', justifyContent: 'center', pt: 1, pb: 0.5 }}>
          <Box sx={{ width: 36, height: 4, borderRadius: 2, bgcolor: colors.borderStrong }} />
        </Box>
        {MORE_NAV_GROUPS.map((group) => {
          const items = moreItems.filter((item) => item.group === group.key);
          if (!items.length) return null;
          return (
            <Box key={group.key} sx={{ px: 1 }}>
              <Typography
                sx={{
                  px: 2,
                  pt: 1.5,
                  pb: 0.5,
                  fontFamily: fonts.mono,
                  fontSize: 11,
                  letterSpacing: '0.1em',
                  textTransform: 'uppercase',
                  color: colors.accent,
                }}
              >
                {group.label}
              </Typography>
              <List dense disablePadding>
                {items.map((item) => {
                  const disabled = Boolean(item.t20Only && !supportsT20OnlyPages);
                  return (
                    <ListItemButton
                      key={item.path}
                      component={Link}
                      to={item.path}
                      disabled={disabled}
                      selected={path === item.path}
                      onClick={() => setMoreOpen(false)}
                      sx={{ minHeight: 48, borderRadius: 2 }}
                    >
                      <ListItemText
                        primary={item.label}
                        secondary={disabled ? "Men's T20 only" : null}
                        primaryTypographyProps={{ fontSize: 16, fontWeight: path === item.path ? 700 : 500 }}
                      />
                    </ListItemButton>
                  );
                })}
              </List>
            </Box>
          );
        })}
        <Divider sx={{ my: 1 }} />
        {MORE_EXTRA_LINKS.filter((item) => !item.group).map((item) => (
          <ListItemButton
            key={item.path}
            component={Link}
            to={item.path}
            onClick={() => setMoreOpen(false)}
            sx={{ minHeight: 48, mx: 1, borderRadius: 2 }}
          >
            <ListItemText primary={item.label} primaryTypographyProps={{ fontSize: 14, color: colors.textLo }} />
          </ListItemButton>
        ))}
      </SwipeableDrawer>
    </>
  );
};

export default MobileBottomNav;
