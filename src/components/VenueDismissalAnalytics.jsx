import React, { useState, useEffect } from 'react';
import { Box, Card, Typography, CircularProgress } from '@mui/material';
import DismissalFieldDesigner from './DismissalFieldDesigner';
import config from '../config';

const VenueDismissalAnalytics = ({
  venue,
  startDate,
  endDate,
  leagues = [],
  includeInternational = false,
  topTeams = null,
  isMobile
}) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!venue || venue === 'All Venues') return;

    const fetchDismissalData = async () => {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams();
        if (startDate) params.set('start_date', startDate);
        if (endDate) params.set('end_date', endDate);
        if (Array.isArray(leagues) && leagues.length > 0) {
          leagues.forEach((league) => params.append('leagues', league));
        }
        params.set('include_international', includeInternational ? 'true' : 'false');
        if (includeInternational && topTeams) {
          params.set('top_teams', String(topTeams));
        }

        // Fetch venue dismissal distribution from deliveries table
        const response = await fetch(
          `${config.API_URL}/venues/${encodeURIComponent(venue)}/dismissals?${params.toString()}`
        );

        if (response.ok) {
          const result = await response.json();
          setData(result);
        } else {
          // Fallback: try a simple query
          setData(null);
        }
      } catch (err) {
        console.error('Error fetching venue dismissal data:', err);
        setError('Failed to load dismissal data');
      } finally {
        setLoading(false);
      }
    };

    fetchDismissalData();
  }, [venue, startDate, endDate, leagues, includeInternational, topTeams]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  if (error || !data) return null;

  return (
    <Card sx={{ p: { xs: 1.5, sm: 2 } }}>
      <Typography variant="h6" gutterBottom>Caught Dismissal Field Design</Typography>
      <Typography variant="body2" color="text.secondary" gutterBottom>
        {data.total_dismissals} total dismissals
      </Typography>
      <DismissalFieldDesigner
        context="venue"
        venue={venue}
        startDate={startDate}
        endDate={endDate}
        leagues={leagues}
        includeInternational={includeInternational}
        topTeams={topTeams}
        isMobile={isMobile}
        summaryData={data}
      />
    </Card>
  );
};

export default VenueDismissalAnalytics;
