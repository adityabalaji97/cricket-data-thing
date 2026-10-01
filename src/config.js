// src/config.js
const config = {
  // Use different API URLs based on environment
  // REACT_APP_API_URL: local dev against an API on another port.
  API_URL: process.env.NODE_ENV === 'production'
    ? '/api'
    : (process.env.REACT_APP_API_URL || 'http://localhost:8000'),
};

export default config;
