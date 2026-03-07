import React from 'react';
import { Chip } from '@mui/material';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';

const ExploreLink = ({ label, to, onClick }) => {
  const handleClick = () => {
    if (onClick) {
      onClick();
    } else if (to) {
      window.open(to, '_blank');
    }
  };

  return (
    <Chip
      label={label || "Explore in Query Builder"}
      icon={<OpenInNewIcon sx={{ fontSize: 16 }} />}
      variant="outlined"
      size="small"
      onClick={handleClick}
      sx={{
        cursor: 'pointer',
        borderColor: 'primary.main',
        color: 'primary.main',
        '&:hover': {
          bgcolor: 'primary.light',
          color: 'primary.contrastText'
        }
      }}
    />
  );
};

export default ExploreLink;
