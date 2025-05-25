// api/proxy.js
const https = require('https');

module.exports = (req, res) => {
  // Get the path from the request
  const path = req.url.replace(/^\/api/, '');
  
  // Determine the origin based on the host
  const host = req.headers.host;
  let origin;
  if (host && host.includes('hindsight2020.vercel.app')) {
    origin = 'https://hindsight2020.vercel.app';
  } else if (host && host.includes('cricket-data-thing.vercel.app')) {
    origin = 'https://cricket-data-thing.vercel.app';
  } else {
    origin = 'https://hindsight2020.vercel.app'; // default to new domain
  }
  
  // Set up the options for the proxied request
  const options = {
    hostname: 'cricket-data-thing-672dfbacf476.herokuapp.com',
    path: path,
    method: req.method,
    headers: {
      'Content-Type': 'application/json',
      'Origin': origin,
      // Copy other headers as needed
    }
  };

  // Make the proxied request
  const proxyReq = https.request(options, (proxyRes) => {
    // Set CORS headers
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    
    // Copy the status code
    res.statusCode = proxyRes.statusCode;
    
    // Copy the headers
    Object.keys(proxyRes.headers).forEach((key) => {
      res.setHeader(key, proxyRes.headers[key]);
    });
    
    // Stream the response
    proxyRes.pipe(res);
  });

  // Handle errors
  proxyReq.on('error', (error) => {
    console.error('Proxy error:', error);
    res.statusCode = 500;
    res.end(JSON.stringify({ error: 'Proxy error', message: error.message }));
  });

  // If there's a request body, write it to the proxied request
  if (req.body) {
    proxyReq.write(req.body);
  }
  
  // End the proxied request
  proxyReq.end();
};