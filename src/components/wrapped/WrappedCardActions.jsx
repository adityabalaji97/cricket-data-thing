import React from 'react';
import { Box, Button, CircularProgress } from '@mui/material';
import ShareIcon from '@mui/icons-material/Share';
import './wrapped.css';

// External link icon component
const ExternalLinkIcon = () => (
  <svg 
    width="14" 
    height="14" 
    viewBox="0 0 24 24" 
    fill="none" 
    stroke="currentColor" 
    strokeWidth="2"
    strokeLinecap="round" 
    strokeLinejoin="round"
  >
    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
    <polyline points="15 3 21 3 21 9" />
    <line x1="10" y1="14" x2="21" y2="3" />
  </svg>
);

// Query/Build icon component
const QueryIcon = () => (
  <svg 
    width="14" 
    height="14" 
    viewBox="0 0 24 24" 
    fill="none" 
    stroke="currentColor" 
    strokeWidth="2"
    strokeLinecap="round" 
    strokeLinejoin="round"
  >
    <circle cx="11" cy="11" r="8" />
    <path d="M21 21l-4.35-4.35" />
  </svg>
);

// Download/Image icon component
const ImageIcon = () => (
  <svg 
    width="16" 
    height="16" 
    viewBox="0 0 24 24" 
    fill="none" 
    stroke="currentColor" 
    strokeWidth="2"
    strokeLinecap="round" 
    strokeLinejoin="round"
  >
    <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
    <circle cx="8.5" cy="8.5" r="1.5" />
    <polyline points="21 15 16 10 5 21" />
  </svg>
);

const WrappedCardActions = ({ deepLinks, onShareImage, isSharing }) => {
  const handleOpenInNewTab = (url) => {
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const handleShare = async () => {
    if (onShareImage) {
      // Use image capture/share
      await onShareImage();
    } else {
      // Fallback to URL share
      const url = window.location.href;
      
      if (navigator.share) {
        try {
          await navigator.share({
            title: 'Hindsight 2025 Wrapped',
            text: 'Check out this T20 cricket stat!',
            url: url,
          });
        } catch (err) {
          console.log('Share cancelled');
        }
      } else {
        // Fallback: copy to clipboard
        navigator.clipboard.writeText(url);
      }
    }
  };

  if (!deepLinks) return null;

  return (
    <Box className="wrapped-card-actions" onClick={(e) => e.stopPropagation()}>
      {/* Team Profile Button */}
      {deepLinks.team_profile && (
        <Button
          variant="contained"
          size="small"
          endIcon={<ExternalLinkIcon />}
          onClick={() => handleOpenInNewTab(deepLinks.team_profile)}
          className="wrapped-action-btn"
        >
          Team Profile
        </Button>
      )}
      
      {/* Venue Analysis Button */}
      {deepLinks.venue_analysis && (
        <Button
          variant="contained"
          size="small"
          endIcon={<ExternalLinkIcon />}
          onClick={() => handleOpenInNewTab(deepLinks.venue_analysis)}
          className="wrapped-action-btn"
        >
          Venue Analysis
        </Button>
      )}

      {/* Query Builder Button */}
      {deepLinks.query_builder && (
        <Button
          variant="outlined"
          size="small"
          startIcon={<QueryIcon />}
          endIcon={<ExternalLinkIcon />}
          onClick={() => handleOpenInNewTab(deepLinks.query_builder)}
          className="wrapped-action-btn wrapped-action-btn-secondary"
        >
          Show data
        </Button>
      )}

      {/* Share Button - Now shares as image */}
      <Button
        variant="text"
        size="small"
        startIcon={isSharing ? <CircularProgress size={14} color="inherit" /> : <ImageIcon />}
        onClick={handleShare}
        className="wrapped-action-btn wrapped-action-btn-share"
        disabled={isSharing}
      >
        {isSharing ? 'Saving...' : 'Save Image'}
      </Button>
    </Box>
  );
};

export default WrappedCardActions;
