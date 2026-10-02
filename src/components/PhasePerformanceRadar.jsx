import React, { useState } from 'react';
import {
  Typography,
  Box,
} from '@mui/material';
import useIsMobile from '../hooks/useIsMobile';
import Card from './ui/Card';
import FilterBar from './ui/FilterBar';
import { SERIES } from '../theme/chartDefaults';

const transformPhaseData = (stats, type = 'overall') => {
  const phases = ['powerplay', 'middle', 'death'];
  const phaseData = [];

  phases.forEach(phase => {
    const phaseStats = type === 'overall'
      ? stats.phase_stats.overall[phase]
      : stats.phase_stats[type][phase];

    phaseData.push({
      phase: phase.charAt(0).toUpperCase() + phase.slice(1),
      'Strike Rate': phaseStats.strike_rate,
      'Average': phaseStats.average || 0,
      'Boundary %': phaseStats.boundary_percentage,
      'Dot %': phaseStats.dot_percentage
    });
  });

  return phaseData;
};

const PhasePerformanceRadar = ({ stats, wrapInCard = true }) => {
  const [selectedView, setSelectedView] = useState('overall');
  const { isMobile } = useIsMobile();

  const data = transformPhaseData(stats, selectedView);

  const metrics = ['Strike Rate', 'Average', 'Boundary %', 'Dot %'];
  const colors = {
    'Strike Rate': SERIES[0],
    'Average': SERIES[2],
    'Boundary %': SERIES[1],
    'Dot %': SERIES[6],
  };

  const filterConfig = [
    {
      key: 'view',
      label: 'View',
      options: [
        { value: 'overall', label: 'Overall' },
        { value: 'pace', label: 'vs Pace' },
        { value: 'spin', label: 'vs Spin' }
      ]
    }
  ];

  const handleFilterChange = (key, value) => {
    if (key === 'view') setSelectedView(value);
  };

  const Wrapper = wrapInCard ? Card : Box;
  const wrapperProps = wrapInCard ? { isMobile } : { sx: { width: '100%' } };

  return (
    <Wrapper {...wrapperProps}>
      <Box sx={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        mb: 2,
        gap: 1,
        flexWrap: isMobile ? 'wrap' : 'nowrap'
      }}>
        <Typography variant={isMobile ? "h6" : "h5"} sx={{ fontWeight: 600, flexShrink: 0 }}>
          By phase
        </Typography>
        <Box sx={{ flexShrink: 1, minWidth: 0 }}>
          <FilterBar
            filters={filterConfig}
            activeFilters={{ view: selectedView }}
            onFilterChange={handleFilterChange}
            isMobile={isMobile}
          />
        </Box>
      </Box>

      {/* Small multiples: one row per metric, each on its own scale. This was a radar overlaying
          four metrics with different units (SR ~150, average ~40, percentages) on one 3-axis
          shape, which made the comparison meaningless and cramped on phones. */}
      <Box sx={{ display: 'grid', gridTemplateColumns: `${isMobile ? 76 : 110}px repeat(3, minmax(0, 1fr))`, columnGap: 1, rowGap: 1.25, alignItems: 'center' }}>
        <Box />
        {data.map((d) => (
          <Typography key={d.phase} sx={{ fontSize: 12, color: 'text.secondary', fontWeight: 600 }}>{d.phase}</Typography>
        ))}
        {metrics.map((metric) => {
          const values = data.map((d) => Number(d[metric]) || 0);
          const max = Math.max(...values, 1e-9);
          return (
            <React.Fragment key={metric}>
              <Typography sx={{ fontSize: 13, color: 'text.secondary', lineHeight: 1.2 }}>
                {metric}{metric === 'Dot %' ? <Box component="span" sx={{ display: 'block', fontSize: 11, color: 'text.disabled' }}>lower is better</Box> : null}
              </Typography>
              {values.map((v, i) => (
                <Box key={`${metric}-${data[i].phase}`} aria-label={`${metric}, ${data[i].phase}: ${v.toFixed(1)}`}>
                  <Typography sx={{ fontFamily: '"IBM Plex Mono", monospace', fontSize: 13, fontWeight: 600 }}>
                    {metric.includes('%') ? `${v.toFixed(1)}%` : v.toFixed(1)}
                  </Typography>
                  <Box sx={{ height: 6, borderRadius: 3, bgcolor: 'rgba(255,255,255,0.06)', mt: 0.5 }}>
                    <Box sx={{ height: '100%', width: `${(v / max) * 100}%`, borderRadius: 3, bgcolor: colors[metric] }} />
                  </Box>
                </Box>
              ))}
            </React.Fragment>
          );
        })}
      </Box>
    </Wrapper>
  );
};

export default PhasePerformanceRadar;
