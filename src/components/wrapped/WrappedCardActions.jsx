import React from 'react';
import { Box, Button } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import BuildIcon from '@mui/icons-material/Build';
import ShareIcon from '@mui/icons-material/Share';
import './wrapped.css';

const WrappedCardActions = ({ deepLinks }) => {
  const navigate = useNavigate();

  const handleOpenInApp = (url) => {
    navigate(url);
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
      {/* Open in App Buttons */}
      {deepLinks.comparison && (
        <Button
          variant="contained"
          size="small"
          startIcon={<OpenInNewIcon />}
          onClick={() => handleOpenInApp(deepLinks.comparison)}
          className="wrapped-action-btn"
        >
          Compare Players
        </Button>
      )}
      
      {deepLinks.team_profile && (
        <Button
          variant="contained"
          size="small"
          startIcon={<OpenInNewIcon />}
          onClick={() => handleOpenInApp(deepLinks.team_profile)}
          className="wrapped-action-btn"
        >
          Team Profile
        </Button>
      )}
      
      {deepLinks.venue_analysis && (
        <Button
          variant="contained"
          size="small"
          startIcon={<OpenInNewIcon />}
          onClick={() => handleOpenInApp(deepLinks.venue_analysis)}
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
          startIcon={<BuildIcon />}
          onClick={() => handleOpenInApp(deepLinks.query_builder)}
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
