/**
 * Scoped dark MUI theme for the match preview (chunk A8).
 *
 * The preview is ~6,000 lines across a dozen child components carrying roughly 370 MUI
 * surfaces — Box, Typography, TableCell, Chip, Card. Restyling those by hand would mean
 * editing every sx block, which is a large diff with a real chance of missing some and
 * leaving the page half-light. A scoped theme restyles all of them at once and stays
 * consistent as those components change.
 *
 * Scoped rather than global on purpose: the rest of the app still renders on the default
 * light theme, and flipping that globally would restyle every page in one untested step.
 * Applied via ThemeProvider around the /venue route only.
 *
 * Tokens come from hindsightDark.js so the preview matches the query builder, scorecard and
 * landing page rather than becoming a fourth palette.
 *
 * Note this cannot reach colours written as literals in a component's own sx — those bypass
 * the palette and are fixed individually.
 */

import { createTheme } from '@mui/material/styles';
import { colors, fonts } from './hindsightDark';

const previewDark = createTheme({
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
      contrastText: colors.bg,
    },
    secondary: {
      main: colors.blue,
    },
    error: { main: colors.red },
    warning: { main: colors.gold },
    info: { main: colors.blue },
    success: { main: colors.accent },
    divider: colors.border,
  },
  typography: {
    fontFamily: fonts.body,
    // Headings use the condensed display face, matching the query builder.
    h1: { fontFamily: fonts.display },
    h2: { fontFamily: fonts.display },
    h3: { fontFamily: fonts.display },
    h4: { fontFamily: fonts.display },
    h5: { fontFamily: fonts.display },
    h6: { fontFamily: fonts.display },
  },
  components: {
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
          fontFamily: fonts.mono,
          fontSize: 12,
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
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
        },
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: { backgroundColor: colors.surface3 },
        bar: { backgroundColor: colors.accent },
      },
    },
  },
});

export default previewDark;
