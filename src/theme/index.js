import { createTheme } from '@mui/material/styles';
import designSystem, { muiTheme, typography } from './designSystem';

const theme = createTheme(muiTheme);

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
