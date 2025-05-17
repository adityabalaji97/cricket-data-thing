// src/config.js
const config = {
  // Use different API URLs based on environment
  API_URL: process.env.NODE_ENV === 'production' 
    ? 'https://cricket-data-thing-672dfbacf476.herokuapp.com' 
    : 'http://localhost:8000',
};

export default config;
