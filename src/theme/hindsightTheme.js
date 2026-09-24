/**
 * The app-wide MUI theme: the Hindsight dark design system.
 *
 * Until U2 the app ran three theme systems at once — a light global MUI theme (designSystem
 * muiTheme), hand-applied hindsightDark tokens on the query builder / landing / scorecard, and a
 * dark theme scoped to the match preview route (previewDark). Pages flipped between light and
 * dark as you navigated, and the nav bar was dark only on /query. This is now the one theme,
 * applied once in src/index.js.
 *
 * Palette and component overrides come from the former previewDark; the type scale, shape and
 * transitions come from designSystem so existing page layouts keep their sizes.
 */

import { createTheme } from '@mui/material/styles';
import { colors, fonts } from './hindsightDark';
import { muiTheme as baseScale } from './designSystem';

const inputBorder = colors.borderStrong;

const hindsightTheme = createTheme({
  palette: {
    mode: 'dark',
    background: {
      default: colors.bg,
      paper: colors.surface1,
    },
    text: {
      primary: colors.textHi,
      secondary: colors.textLo,
      disabled: colors.textFaint,
    },
    primary: {
      main: colors.accent,
      // Components use primary.light as a soft tint behind icons and on hover (as it is in
      // MUI's light mode), not as a brighter accent, so it is the translucent accent here.
      light: colors.accentSoft,
      dark: '#8fc93a',
      contrastText: colors.bg,
    },
    secondary: {
      main: colors.blue,
      contrastText: colors.bg,
    },
    error: { main: colors.red },
    warning: { main: colors.gold },
    info: { main: colors.blue },
    success: { main: colors.accent, contrastText: colors.bg },
    divider: colors.border,
    action: {
      hover: 'rgba(255,255,255,0.05)',
      selected: colors.accentSoft,
      disabledBackground: 'rgba(255,255,255,0.08)',
    },
  },

  typography: {
    ...baseScale.typography,
    fontFamily: fonts.body,
    // Headings use the condensed display face, matching the query builder.
    h1: { ...baseScale.typography.h1, fontFamily: fonts.display },
    h2: { ...baseScale.typography.h2, fontFamily: fonts.display },
    h3: { ...baseScale.typography.h3, fontFamily: fonts.display },
    h4: { ...baseScale.typography.h4, fontFamily: fonts.display },
    h5: { ...baseScale.typography.h5, fontFamily: fonts.display },
    h6: { ...baseScale.typography.h6, fontFamily: fonts.display },
    button: { fontFamily: fonts.body, fontWeight: 600 },
  },

  shape: baseScale.shape,
  transitions: baseScale.transitions,

  components: {
    MuiCssBaseline: {
      styleOverrides: {
        // color-scheme makes native controls (date-picker icons, scrollbars, autofill) render
        // for a dark page instead of dark-on-dark. html gets the background too, so iOS
        // overscroll "bounce" shows the page colour rather than a light flash.
        html: { colorScheme: 'dark', backgroundColor: colors.bg },
        body: {
          backgroundColor: colors.bg,
          color: colors.textHi,
          WebkitFontSmoothing: 'antialiased',
        },
        '::selection': { backgroundColor: colors.accentSoft },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: { backgroundColor: colors.bg, backgroundImage: 'none', boxShadow: 'none' },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundColor: colors.surface1,
          backgroundImage: 'none',
          border: `1px solid ${colors.border}`,
          borderRadius: 16,
          boxShadow: 'none',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        // MUI's dark mode lightens Paper by elevation, which reads as washed-out grey against
        // this palette. Flat surfaces with a hairline border instead.
        root: {
          backgroundImage: 'none',
          backgroundColor: colors.surface1,
        },
      },
    },
    MuiMenu: {
      styleOverrides: {
        paper: { backgroundColor: colors.surface2, border: `1px solid ${colors.borderStrong}` },
      },
    },
    MuiPopover: {
      styleOverrides: {
        paper: { backgroundColor: colors.surface2, border: `1px solid ${colors.borderStrong}` },
      },
    },
    MuiAutocomplete: {
      styleOverrides: {
        paper: { backgroundColor: colors.surface2, border: `1px solid ${colors.borderStrong}` },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: { backgroundColor: colors.surface1, backgroundImage: 'none' },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: { backgroundColor: colors.surface1, border: `1px solid ${colors.border}` },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          backgroundColor: colors.input,
          '& .MuiOutlinedInput-notchedOutline': { borderColor: inputBorder },
          '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.24)' },
          '&.Mui-focused .MuiOutlinedInput-notchedOutline': { borderColor: colors.accent },
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: { textTransform: 'none', borderRadius: 10 },
        outlined: { borderColor: inputBorder },
      },
    },
    MuiToggleButton: {
      styleOverrides: {
        root: {
          color: colors.textLo,
          borderColor: inputBorder,
          '&.Mui-selected': {
            color: colors.bg,
            backgroundColor: colors.accent,
            '&:hover': { backgroundColor: colors.accentHover },
          },
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderBottomColor: colors.border,
          color: colors.textHi,
        },
        head: {
          color: colors.textLo,
          fontFamily: fonts.mono,
          fontSize: 11,
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
          backgroundColor: colors.surface2,
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          backgroundColor: colors.surface3,
          color: colors.textMed,
          border: `1px solid ${colors.border}`,
        },
        // Filled coloured chips keep their semantic colour; only the default grey chip is
        // restyled above. MUI applies these after root, so they win.
        colorPrimary: { backgroundColor: colors.accent, color: colors.bg, borderColor: 'transparent' },
        colorSecondary: { backgroundColor: colors.blue, color: colors.bg, borderColor: 'transparent' },
        colorSuccess: { backgroundColor: colors.accent, color: colors.bg, borderColor: 'transparent' },
        colorError: { backgroundColor: colors.red, color: colors.textHi, borderColor: 'transparent' },
        colorWarning: { backgroundColor: colors.gold, color: colors.bg, borderColor: 'transparent' },
        colorInfo: { backgroundColor: colors.blue, color: colors.bg, borderColor: 'transparent' },
        outlined: { backgroundColor: 'transparent', borderColor: inputBorder },
      },
    },
    MuiTabs: {
      styleOverrides: {
        indicator: { backgroundColor: colors.accent },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: {
          color: colors.textLo,
          fontFamily: fonts.display,
          fontWeight: 700,
          letterSpacing: '0.02em',
          '&.Mui-selected': { color: colors.accent },
        },
      },
    },
    MuiDivider: {
      styleOverrides: { root: { borderColor: colors.border } },
    },
    MuiTooltip: {
      styleOverrides: {
        tooltip: {
          backgroundColor: colors.surface3,
          color: colors.textHi,
          border: `1px solid ${colors.borderStrong}`,
          fontFamily: fonts.body,
          fontSize: 12,
        },
      },
    },
    MuiAccordion: {
      styleOverrides: {
        root: {
          backgroundColor: colors.surface1,
          backgroundImage: 'none',
          border: `1px solid ${colors.border}`,
          boxShadow: 'none',
          '&:before': { display: 'none' },
        },
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: { backgroundColor: colors.surface3 },
        bar: { backgroundColor: colors.accent },
      },
    },
    MuiBottomNavigation: {
      styleOverrides: {
        root: { backgroundColor: colors.surface1, height: 60 },
      },
    },
    MuiBottomNavigationAction: {
      styleOverrides: {
        root: {
          color: colors.textLo,
          minWidth: 0,
          padding: '6px 0',
          '&.Mui-selected': { color: colors.accent },
        },
        label: {
          fontFamily: fonts.body,
          fontSize: 11,
          '&.Mui-selected': { fontSize: 11 },
        },
      },
    },
  },
});

export default hindsightTheme;
