// src/config.js
const config = {
  // Use different API URLs based on environment
  API_URL: process.env.NODE_ENV === 'production' 
    ? '/api' 
    : 'http://localhost:8000',
};

export default config;
