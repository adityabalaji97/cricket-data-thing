import React from 'react';
import { Card, Typography, Chip, Stack } from '@mui/material';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { getBatterContextualQueries, getBowlerContextualQueries } from '../../../utils/queryBuilderLinks';

const ExploreSection = ({ playerName, mode, dateRange, venue }) => {
  const context = {
    startDate: dateRange?.start,
    endDate: dateRange?.end,
    venue,
  };

  const links = mode === 'bowling'
    ? getBowlerContextualQueries(playerName, context)
    : getBatterContextualQueries(playerName, context);

  return (
    <Card sx={{ p: { xs: 1.5, sm: 2 } }}>
      <Typography variant="h6" gutterBottom>
        Explore More
      </Typography>
      <Typography variant="body2" color="text.secondary" gutterBottom>
        Dive deeper into the data with pre-built queries
      </Typography>
      <Stack direction="row" flexWrap="wrap" gap={1} sx={{ mt: 2 }}>
        {(links || []).map((link, idx) => (
          <Chip
            key={idx}
            label={link.question || link.label}
            icon={<OpenInNewIcon sx={{ fontSize: 14 }} />}
            variant="outlined"
            size="small"
            component="a"
            href={link.url}
            clickable
            sx={{
              cursor: 'pointer',
              borderColor: 'primary.light',
              '&:hover': { bgcolor: 'primary.light' }
            }}
          />
        ))}
      </Stack>
    </Card>
  );
};

export default ExploreSection;
