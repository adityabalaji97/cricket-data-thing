// Script to automatically fill the player dropdown and click GO
// This will be placed in the public/index.html script tag or added to the index.js file

// Wait for the document to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
  // Function to check URL parameters and auto-trigger player loading
  function checkAndAutoLoadPlayer() {
    // Check if we're on the player page
    if (window.location.pathname === '/player') {
      const params = new URLSearchParams(window.location.search);
      const playerName = params.get('name');
      const autoload = params.get('autoload') === 'true';
      const startDate = params.get('start_date');
      const endDate = params.get('end_date');
      const venue = params.get('venue');
      
      if (playerName && autoload) {
        console.log('Auto-loading player detected:', playerName);
        console.log('Parameters:', { startDate, endDate, venue });
        
        // Set a delay to ensure React components are fully mounted
        setTimeout(function() {
          // Try to find and set the player in the dropdown
          const playerInput = document.querySelector('input[id^="mui-"][placeholder="Select Player"]');
          const goButton = document.getElementById('go-button');
          const startDateInput = document.querySelector('input[type="date"][value]');
          const endDateInput = document.querySelectorAll('input[type="date"][value]')[1];
          const venueInput = document.querySelector('input[id^="mui-"][placeholder="Select Venue"]');
          
          // Set the start date if provided and input exists
          if (startDate && startDateInput) {
            console.log('Setting start date:', startDate);
            startDateInput.value = startDate;
            startDateInput.dispatchEvent(new Event('input', { bubbles: true }));
            startDateInput.dispatchEvent(new Event('change', { bubbles: true }));
          }
          
          // Set the end date if provided and input exists
          if (endDate && endDateInput) {
            console.log('Setting end date:', endDate);
            endDateInput.value = endDate;
            endDateInput.dispatchEvent(new Event('input', { bubbles: true }));
            endDateInput.dispatchEvent(new Event('change', { bubbles: true }));
          }
          
          // Set the venue if provided and input exists
          if (venue && venueInput) {
            console.log('Setting venue:', venue);
            venueInput.value = venue;
            venueInput.dispatchEvent(new Event('input', { bubbles: true }));
            venueInput.dispatchEvent(new Event('change', { bubbles: true }));
          }
          
          if (playerInput && goButton) {
            console.log('Found player input and GO button');
            
            // Attempt to set the player name in the input
            playerInput.value = playerName;
            playerInput.dispatchEvent(new Event('input', { bubbles: true }));
            playerInput.dispatchEvent(new Event('change', { bubbles: true }));
            
            // Give everything a moment to update
            setTimeout(() => {
              // Try to click the GO button
              if (!goButton.disabled) {
                console.log('Clicking GO button');
                goButton.click();
              } else {
                console.log('GO button is disabled');
              }
            }, 300);
          } else {
            console.log('Could not find player input or GO button');
          }
        }, 1000);
      }
    }
  }
  
  // Run the check on page load
  checkAndAutoLoadPlayer();
  
  // Also run it on history changes (for SPA navigation)
  window.addEventListener('popstate', checkAndAutoLoadPlayer);
});
