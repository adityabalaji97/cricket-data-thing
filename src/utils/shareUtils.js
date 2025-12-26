/**
 * Utilities for capturing and sharing Wrapped cards as images
 */

/**
 * Dynamically import html2canvas to avoid build issues if not installed
 */
const getHtml2Canvas = async () => {
  try {
    const html2canvas = await import('html2canvas');
    return html2canvas.default;
  } catch (error) {
    console.error('html2canvas not installed. Run: npm install html2canvas');
    return null;
  }
};

/**
 * Capture a DOM element as a PNG data URL
 * Handles overlay/backdrop cleanup to prevent grey tint issues
 * @param {HTMLElement} element - The DOM element to capture
 * @returns {Promise<string|null>} - Base64 data URL of the image
 */
export const captureElementAsImage = async (element) => {
  if (!element) {
    console.error('No element provided to capture');
    return null;
  }

  const html2canvas = await getHtml2Canvas();
  if (!html2canvas) return null;

  // Track elements we've modified so we can restore them
  const modifiedElements = [];

  try {
    // STEP 1: Hide overlay elements that cause grey tint
    const overlaySelectors = [
      '.MuiBackdrop-root',
      '.MuiModal-root',
      '.wrapped-nav-hints',
      '.wrapped-action-btn-share',
      '.wrapped-top-section',
      '.wrapped-card-actions',
      '[class*="Backdrop"]',
      '[class*="backdrop"]'
    ];
    
    overlaySelectors.forEach(selector => {
      document.querySelectorAll(selector).forEach(el => {
        if (el.style.display !== 'none') {
          modifiedElements.push({
            element: el,
            property: 'display',
            originalValue: el.style.display
          });
          el.style.display = 'none';
        }
      });
    });

    // STEP 2: Temporarily set solid background on element
    const originalBg = element.style.backgroundColor;
    element.style.backgroundColor = '#121212';
    modifiedElements.push({
      element: element,
      property: 'backgroundColor',
      originalValue: originalBg
    });

    // STEP 3: Remove filter/opacity from parent containers and element
    const container = element.closest('.wrapped-container');
    if (container) {
      // Store and clear filter
      if (container.style.filter) {
        modifiedElements.push({
          element: container,
          property: 'filter',
          originalValue: container.style.filter
        });
        container.style.filter = 'none';
      }
      // Store and set full opacity
      modifiedElements.push({
        element: container,
        property: 'opacity',
        originalValue: container.style.opacity
      });
      container.style.opacity = '1';
    }

    // Also check the card itself
    modifiedElements.push({
      element: element,
      property: 'filter',
      originalValue: element.style.filter
    });
    element.style.filter = 'none';
    
    modifiedElements.push({
      element: element,
      property: 'opacity', 
      originalValue: element.style.opacity
    });
    element.style.opacity = '1';

    // Small delay to ensure DOM updates are applied
    await new Promise(resolve => setTimeout(resolve, 100));

    // STEP 4: Capture the element
    const canvas = await html2canvas(element, {
      backgroundColor: '#121212', // Match wrapped background
      scale: 2, // Higher quality for retina displays
      useCORS: true,
      logging: false,
      allowTaint: true,
      width: element.offsetWidth,
      height: element.offsetHeight,
      // Ignore elements that might cause overlay issues
      ignoreElements: (el) => {
        // Skip if element or its classes contain these patterns
        const classNames = el.className || '';
        const classStr = typeof classNames === 'string' ? classNames : classNames.toString();
        
        return (
          classStr.includes('MuiBackdrop') ||
          classStr.includes('wrapped-nav-hints') ||
          classStr.includes('wrapped-action-btn-share') ||
          classStr.includes('wrapped-top-section') ||
          classStr.includes('wrapped-card-actions') ||
          classStr.includes('Backdrop') ||
          classStr.includes('progress-') ||
          el.tagName === 'NOSCRIPT'
        );
      },
      // Ensure we capture with solid background
      onclone: (clonedDoc, clonedElement) => {
        // Ensure the cloned element has solid background
        clonedElement.style.backgroundColor = '#121212';
        clonedElement.style.filter = 'none';
        clonedElement.style.opacity = '1';
        clonedElement.style.paddingTop = '40px'; // Reduce top padding since we hide header
        
        // Remove any potential overlay elements from the clone
        const selectorsToRemove = [
          '.MuiBackdrop-root',
          '.wrapped-nav-hints',
          '.wrapped-card-actions',
          '.wrapped-top-section',
          '[class*="Backdrop"]'
        ];
        
        selectorsToRemove.forEach(selector => {
          clonedDoc.querySelectorAll(selector).forEach(el => el.remove());
        });
        
        // Also remove from cloned element itself if nested
        selectorsToRemove.forEach(selector => {
          clonedElement.querySelectorAll(selector).forEach(el => el.remove());
        });
      }
    });

    return canvas.toDataURL('image/png');
  } catch (error) {
    console.error('Error capturing element:', error);
    return null;
  } finally {
    // STEP 5: Restore all modified elements
    modifiedElements.forEach(({ element: el, property, originalValue }) => {
      el.style[property] = originalValue || '';
    });
  }
};

/**
 * Download an image from a data URL
 * @param {string} dataUrl - Base64 data URL
 * @param {string} filename - Filename for download
 */
export const downloadImage = (dataUrl, filename = 'hindsight-wrapped.png') => {
  const link = document.createElement('a');
  link.download = filename;
  link.href = dataUrl;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

/**
 * Share an image using Web Share API or fallback to download
 * @param {string} dataUrl - Base64 data URL of the image
 * @param {string} title - Title for sharing
 * @param {string} text - Description text for sharing
 * @returns {Promise<boolean>} - Whether sharing was successful
 */
export const shareImage = async (dataUrl, title = 'Hindsight Wrapped 2025', text = 'Check out my cricket stats!') => {
  try {
    // Convert data URL to blob
    const response = await fetch(dataUrl);
    const blob = await response.blob();
    const file = new File([blob], 'hindsight-wrapped.png', { type: 'image/png' });

    // Check if Web Share API with files is supported
    if (navigator.share && navigator.canShare && navigator.canShare({ files: [file] })) {
      await navigator.share({
        files: [file],
        title: title,
        text: text,
      });
      return true;
    } else {
      // Fallback: download the image
      downloadImage(dataUrl, `hindsight-wrapped-${Date.now()}.png`);
      return true;
    }
  } catch (error) {
    if (error.name === 'AbortError') {
      // User cancelled sharing
      console.log('Share cancelled');
      return false;
    }
    console.error('Error sharing:', error);
    // Fallback to download on error
    downloadImage(dataUrl, `hindsight-wrapped-${Date.now()}.png`);
    return true;
  }
};

/**
 * Capture and share a card element
 * @param {HTMLElement} element - The card element to capture
 * @param {string} cardTitle - Title of the card for filename
 * @returns {Promise<boolean>} - Whether the operation was successful
 */
export const captureAndShare = async (element, cardTitle = 'card') => {
  const dataUrl = await captureElementAsImage(element);
  if (!dataUrl) {
    console.error('Failed to capture image');
    return false;
  }

  const sanitizedTitle = cardTitle.toLowerCase().replace(/[^a-z0-9]+/g, '-');
  return shareImage(
    dataUrl,
    `Hindsight Wrapped 2025 - ${cardTitle}`,
    `Check out this T20 cricket stat from Hindsight Wrapped 2025!`
  );
};

export default {
  captureElementAsImage,
  downloadImage,
  shareImage,
  captureAndShare,
};
