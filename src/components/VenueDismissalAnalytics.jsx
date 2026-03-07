import React, { useState, useEffect } from 'react';
import { Box, Card, Typography, CircularProgress, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from '@mui/material';
import DismissalDonutChart from './charts/DismissalDonutChart';
import ExploreLink from './ui/ExploreLink';
import config from '../config';

const DISMISSAL_LABELS = {
  'bowled': 'Bowled',
  'caught': 'Caught',
  'caught and bowled': 'C & B',
  'lbw': 'LBW',
  'stumped': 'Stumped',
  'run out': 'Run Out',
  'hit wicket': 'Hit Wicket'
};

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
      <Typography variant="h6" gutterBottom>Dismissal Patterns</Typography>
      <Typography variant="body2" color="text.secondary" gutterBottom>
        {data.total_dismissals} total dismissals
      </Typography>

      <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: 3 }}>
        <Box sx={{ flex: 1 }}>
          <DismissalDonutChart
            data={data.dismissals}
            title="How Batters Get Out"
            isMobile={isMobile}
          />
        </Box>

        {data.by_phase && Object.keys(data.by_phase).length > 0 && (
          <Box sx={{ flex: 1 }}>
            <TableContainer>
              <Typography variant="subtitle2" gutterBottom>By Phase</Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Type</TableCell>
                    <TableCell align="right">PP</TableCell>
                    <TableCell align="right">Mid</TableCell>
                    <TableCell align="right">Death</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {data.dismissals.slice(0, 6).map(d => (
                    <TableRow key={d.type} sx={{ '&:nth-of-type(odd)': { bgcolor: 'rgba(0,0,0,0.04)' } }}>
                      <TableCell>{DISMISSAL_LABELS[d.type] || d.type}</TableCell>
                      {['powerplay', 'middle', 'death'].map(phase => {
                        const entry = (data.by_phase[phase] || []).find(p => p.type === d.type);
                        return <TableCell key={phase} align="right">{entry?.count || 0}</TableCell>;
                      })}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        )}
      </Box>

      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
        <ExploreLink
          label="Explore dismissal patterns at this venue"
          to={`/query?venue=${encodeURIComponent(venue)}&group_by=dismissal`}
        />
      </Box>
    </Card>
  );
};

export default VenueDismissalAnalytics;
