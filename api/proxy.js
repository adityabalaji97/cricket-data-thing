// api/proxy.js
const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = (req, res) => {
  // Create the proxy middleware
  const proxy = createProxyMiddleware({
    target: 'https://cricket-data-thing-672dfbacf476.herokuapp.com',
    changeOrigin: true,
    pathRewrite: {
      '^/api': ''
    }
  });
  
  return proxy(req, res);
};
