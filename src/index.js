import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';
import { Analytics } from '@vercel/analytics/react';
import { ThemeProvider, CssBaseline } from '@mui/material';
import { theme } from './theme';
import { cssVariables } from './theme/hindsightDark';
import { FormatProvider } from './context/FormatContext';

// Publish the dark-theme tokens as CSS custom properties so stylesheets that cannot import JS
// — matchScorecard.css in particular — can use var(--hs-*) instead of repeating hex literals.
Object.entries(cssVariables).forEach(([name, value]) => {
  document.documentElement.style.setProperty(name, value);
});

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <FormatProvider>
        <App />
      </FormatProvider>
      <Analytics />
    </ThemeProvider>
  </React.StrictMode>
);

reportWebVitals();
