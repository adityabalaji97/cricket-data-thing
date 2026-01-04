import { createTheme } from '@mui/material/styles';
import designSystem, { muiTheme } from './designSystem';

const theme = createTheme(muiTheme);

export { theme };
export * from './designSystem';
export default theme;
export { designSystem };
