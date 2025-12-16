import React from 'react';
import { Box, Button } from '@mui/material';
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

const WrappedCardActions = ({ deepLinks }) => {
  const handleOpenInNewTab = (url) => {
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const handleShare = async () => {
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
  };

  if (!deepLinks) return null;

  return (
    <Box className="wrapped-card-actions" onClick={(e) => e.stopPropagation()}>
      {/* Open in App Buttons - Now open in new tab */}
      {deepLinks.comparison && (
        <Button
          variant="contained"
          size="small"
          endIcon={<ExternalLinkIcon />}
          onClick={() => handleOpenInNewTab(deepLinks.comparison)}
          className="wrapped-action-btn"
        >
          Compare Players
        </Button>
      )}
      
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
          Recreate Query
        </Button>
      )}

      {/* Share Button */}
      <Button
        variant="text"
        size="small"
        startIcon={<ShareIcon />}
        onClick={handleShare}
        className="wrapped-action-btn wrapped-action-btn-share"
      >
        Share
      </Button>
    </Box>
  );
};

export default WrappedCardActions;
