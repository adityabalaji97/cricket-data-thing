# Adding Vercel Analytics to Cricket Data Thing

Vercel Analytics has been added to the application to track usage metrics. Here's what has been done and what you need to do if you're setting up the project from scratch:

## What's Been Done

1. Added the `@vercel/analytics` package to the project dependencies
2. Integrated the `Analytics` component in the main app entry point (`src/index.js`)

## How to Set Up Manually

If you need to set up Vercel Analytics from scratch, follow these steps:

1. Install the package:
   ```bash
   npm install @vercel/analytics
   # or 
   yarn add @vercel/analytics
   ```

2. Import and add the Analytics component to your app:
   ```jsx
   // In src/index.js or your main entry file
   import { Analytics } from '@vercel/analytics/react';

   // Then add it to your component tree
   ReactDOM.render(
     <React.StrictMode>
       <App />
       <Analytics />
     </React.StrictMode>,
     document.getElementById('root')
   );
   ```

3. Deploy to Vercel - the analytics will automatically be enabled for your project.

## Benefits of Vercel Analytics

- Real-time analytics dashboard in your Vercel project
- Automatic page view tracking
- Privacy-focused with no cookies required
- Core Web Vitals monitoring
- Zero impact on your application's performance

## Accessing Analytics

After deploying to Vercel, you can access your analytics dashboard from your Vercel project's page in the "Analytics" tab.

## Quick Install Script

A script has been provided to install Vercel Analytics:

```bash
# Make the script executable
chmod +x install-vercel-analytics.sh

# Run the script
./install-vercel-analytics.sh
```
