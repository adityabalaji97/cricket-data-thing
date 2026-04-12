// api/proxy.js
const https = require('https');

const ALLOWED_ORIGINS = new Set([
  'http://localhost:3000',
  'https://cricket-data-thing.vercel.app',
  'https://hindsight2020.vercel.app',
]);

const getAllowedOrigin = (requestOrigin) => (
  requestOrigin && ALLOWED_ORIGINS.has(requestOrigin) ? requestOrigin : null
);

const getProxyOrigin = (host, requestOrigin) => {
  const allowedOrigin = getAllowedOrigin(requestOrigin);
  if (allowedOrigin) {
    return allowedOrigin;
  }

  if (host && host.includes('hindsight2020.vercel.app')) {
    return 'https://hindsight2020.vercel.app';
  }

  if (host && host.includes('cricket-data-thing.vercel.app')) {
    return 'https://cricket-data-thing.vercel.app';
  }

  return 'https://hindsight2020.vercel.app';
};

const applyCorsHeaders = (req, res) => {
  const allowedOrigin = getAllowedOrigin(req.headers.origin);

  if (allowedOrigin) {
    res.setHeader('Access-Control-Allow-Origin', allowedOrigin);
    res.setHeader('Access-Control-Allow-Credentials', 'true');
    res.setHeader('Vary', 'Origin');
  }

  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader(
    'Access-Control-Allow-Headers',
    req.headers['access-control-request-headers'] || 'Content-Type'
  );
};

module.exports = (req, res) => {
  // Get the path from the request
  const path = req.url.replace(/^\/api/, '');
  const host = req.headers.host;
  const requestOrigin = req.headers.origin;
  const proxyOrigin = getProxyOrigin(host, requestOrigin);

  if (req.method === 'OPTIONS') {
    applyCorsHeaders(req, res);
    res.statusCode = 204;
    res.end();
    return;
  }
  
  // Set up the options for the proxied request
  const options = {
    hostname: 'cricket-data-thing-672dfbacf476.herokuapp.com',
    path: path,
    method: req.method,
    headers: {
      'Content-Type': 'application/json',
      'Origin': proxyOrigin,
      // Copy other headers as needed
    }
  };

  // Make the proxied request
  const proxyReq = https.request(options, (proxyRes) => {
    // Copy the status code
    res.statusCode = proxyRes.statusCode;
    
    // Copy the headers
    Object.keys(proxyRes.headers).forEach((key) => {
      if (key.toLowerCase().startsWith('access-control-')) {
        return;
      }
      res.setHeader(key, proxyRes.headers[key]);
    });

    applyCorsHeaders(req, res);
    
    // Stream the response
    proxyRes.pipe(res);
  });

  // Handle errors
  proxyReq.on('error', (error) => {
    console.error('Proxy error:', error);
    res.statusCode = 500;
    res.end(JSON.stringify({ error: 'Proxy error', message: error.message }));
  });

  // Forward the request body for POST/PUT/PATCH
  if (req.method !== 'GET' && req.method !== 'HEAD' && req.method !== 'OPTIONS') {
    if (req.body) {
      // Vercel may pre-parse body as object or provide as string/Buffer
      const payload = typeof req.body === 'string' || Buffer.isBuffer(req.body)
        ? req.body
        : JSON.stringify(req.body);
      proxyReq.setHeader('Content-Length', Buffer.byteLength(payload));
      proxyReq.end(payload);
    } else {
      // Stream raw body if not pre-parsed
      req.pipe(proxyReq);
    }
  } else {
    proxyReq.end();
  }
};
