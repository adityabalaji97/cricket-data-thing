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

  try {
    const canvas = await html2canvas(element, {
      backgroundColor: '#121212', // Match wrapped background
      scale: 2, // Higher quality for retina displays
      useCORS: true,
      logging: false,
      allowTaint: true,
      // Capture the full element
      width: element.offsetWidth,
      height: element.offsetHeight,
    });

    return canvas.toDataURL('image/png');
  } catch (error) {
    console.error('Error capturing element:', error);
    return null;
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
