import React from 'react';
import { Box, Card, Typography, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from '@mui/material';
import DismissalDonutChart from '../../charts/DismissalDonutChart';
import ExploreLink from '../../ui/ExploreLink';
import { buildQueryUrl } from '../../../utils/queryBuilderLinks';

const DISMISSAL_LABELS = {
  'bowled': 'Bowled',
  'caught': 'Caught',
  'caught and bowled': 'C & B',
  'lbw': 'LBW',
  'stumped': 'Stumped',
  'run out': 'Run Out',
  'hit wicket': 'Hit Wicket'
};

const PhaseBreakdownTable = ({ byPhase, isMobile }) => {
  if (!byPhase || Object.keys(byPhase).length === 0) return null;

  const phases = ['powerplay', 'middle', 'death'];
  const phaseLabels = { powerplay: 'Powerplay', middle: 'Middle', death: 'Death' };

  // Collect all dismissal types
  const allTypes = new Set();
  phases.forEach(phase => {
    (byPhase[phase] || []).forEach(d => allTypes.add(d.type));
  });

  return (
    <TableContainer>
      <Typography variant="subtitle2" gutterBottom>Phase-wise Breakdown</Typography>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Type</TableCell>
            {phases.map(p => (
              <TableCell key={p} align="right">{phaseLabels[p]}</TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {[...allTypes].map(type => (
            <TableRow key={type} sx={{ '&:nth-of-type(odd)': { bgcolor: 'rgba(0,0,0,0.04)' } }}>
              <TableCell>{DISMISSAL_LABELS[type] || type}</TableCell>
              {phases.map(phase => {
                const entry = (byPhase[phase] || []).find(d => d.type === type);
                return <TableCell key={phase} align="right">{entry?.count || 0}</TableCell>;
              })}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

const DismissalSection = ({ dismissalData, mode, playerName, isMobile }) => {
  if (!dismissalData || !dismissalData.dismissals || dismissalData.dismissals.length === 0) {
    return (
      <Box sx={{ p: 2, textAlign: 'center' }}>
        <Typography color="text.secondary">No dismissal data available</Typography>
      </Box>
    );
  }

  const title = mode === 'bowling'
    ? `How ${playerName} Takes Wickets`
    : `How ${playerName} Gets Out`;

  const totalLabel = mode === 'bowling'
    ? `${dismissalData.total_wickets || dismissalData.total_dismissals} total wickets`
    : `${dismissalData.total_dismissals || dismissalData.total_wickets} total dismissals`;

  const exploreUrl = mode === 'bowling'
    ? buildQueryUrl({ bowlers: [playerName] }, ['dismissal'])
    : buildQueryUrl({ batters: [playerName] }, ['dismissal']);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Card sx={{ p: { xs: 1.5, sm: 2 } }}>
        <Typography variant="body2" color="text.secondary" align="center" gutterBottom>
          {totalLabel}
        </Typography>
        <DismissalDonutChart
          data={dismissalData.dismissals}
          title={title}
          isMobile={isMobile}
        />
      </Card>

      {dismissalData.by_phase && Object.keys(dismissalData.by_phase).length > 0 && (
        <Card sx={{ p: { xs: 1.5, sm: 2 } }}>
          <PhaseBreakdownTable byPhase={dismissalData.by_phase} isMobile={isMobile} />
        </Card>
      )}

      <Box sx={{ display: 'flex', justifyContent: 'center' }}>
        <ExploreLink
          label={mode === 'bowling' ? "Explore wicket-taking methods" : "Explore dismissal patterns"}
          to={exploreUrl}
        />
      </Box>
    </Box>
  );
};

export default DismissalSection;
