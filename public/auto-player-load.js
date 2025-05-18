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
      
      if (playerName && autoload) {
        console.log('Auto-loading player detected:', playerName);
        
        // Set a delay to ensure React components are fully mounted
        setTimeout(function() {
          // Try to find and set the player in the dropdown
          const playerInput = document.querySelector('input[id^="mui-"][placeholder="Select Player"]');
          const goButton = document.getElementById('go-button');
          
          if (playerInput && goButton) {
            console.log('Found player input and GO button');
            
            // Attempt to set the player name in the input
            playerInput.value = playerName;
            playerInput.dispatchEvent(new Event('input', { bubbles: true }));
            playerInput.dispatchEvent(new Event('change', { bubbles: true }));
            
            // Try to click the GO button
            if (!goButton.disabled) {
              console.log('Clicking GO button');
              goButton.click();
            } else {
              console.log('GO button is disabled');
            }
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
