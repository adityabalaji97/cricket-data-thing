import hindsightTheme from './hindsightTheme';
import designSystem, { typography } from './designSystem';

// The single app-wide theme (dark). See hindsightTheme.js for why there is only one.
const theme = hindsightTheme;

theme.typography.h3 = {
  ...theme.typography.h3,
  [theme.breakpoints.down('sm')]: {
    fontSize: typography.fontSize.xl,
  },
};

export { theme };
export * from './designSystem';
export default theme;
export { designSystem };
