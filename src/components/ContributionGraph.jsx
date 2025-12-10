import React, { useMemo } from 'react';
import { Box, Typography, Tooltip, Paper } from '@mui/material';
import {
  getBatterColor,
  getBowlerColor,
  getWeeksBetween,
  formatDateKey,
  getMonthLabels,
  createInningsMap,
  DAY_LABELS
} from './contributionGraphUtils';

const CELL_SIZE = 12;
const CELL_GAP = 3;

/**
 * GitHub-style contribution graph for cricket innings
 * 
 * @param {Object} props
 * @param {Array} props.innings - Array of innings with date, fantasy_points, runs (for batters)
 * @param {string} props.mode - 'batter' or 'bowler'
 * @param {Object} props.dateRange - { start: 'YYYY-MM-DD', end: 'YYYY-MM-DD' }
 */
const ContributionGraph = ({ innings = [], mode = 'batter', dateRange }) => {
  // Create data structures for rendering
  const { weeks, monthLabels, inningsMap } = useMemo(() => {
    if (!dateRange?.start || !dateRange?.end) {
      return { weeks: [], monthLabels: [], inningsMap: new Map() };
    }
    
    const weeks = getWeeksBetween(dateRange.start, dateRange.end);
    const monthLabels = getMonthLabels(weeks);
    const inningsMap = createInningsMap(innings);
    
    return { weeks, monthLabels, inningsMap };
  }, [innings, dateRange]);

  // Get color based on mode and score
  const getColor = (score, isDuck) => {
    if (mode === 'batter') {
      return getBatterColor(score, isDuck);
    }
    return getBowlerColor(score);
  };

  // Render a single cell
  const renderCell = (date) => {
    const dateKey = formatDateKey(date);
    const inning = inningsMap.get(dateKey);
    const hasMatch = !!inning;
    
    // For batters, check if it's a duck
    const isDuck = mode === 'batter' && hasMatch && inning.runs === 0;
    const fantasyPoints = hasMatch ? (inning.fantasy_points || 0) : 0;
    const color = hasMatch ? getColor(fantasyPoints, isDuck) : '#ebedf0';
    
    // Build tooltip content
    let tooltipContent = '';
    if (hasMatch) {
      const dateStr = new Date(date).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      });
      
      if (mode === 'batter') {
        const sr = inning.strike_rate || 0;
        tooltipContent = `${dateStr}\nvs ${inning.bowling_team}\n${inning.runs}(${inning.balls_faced}) SR: ${sr}\nFantasy: ${fantasyPoints.toFixed(1)}`;
      } else {
        tooltipContent = `${dateStr}\nvs ${inning.batting_team}\n${inning.wickets}/${inning.runs} (${inning.overs} ov)\nFantasy: ${fantasyPoints.toFixed(1)}`;
      }
    } else {
      tooltipContent = new Date(date).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      }) + '\nNo match';
    }

    return (
      <Tooltip 
        key={dateKey} 
        title={<span style={{ whiteSpace: 'pre-line' }}>{tooltipContent}</span>}
        arrow
        placement="top"
      >
        <Box
          sx={{
            width: CELL_SIZE,
            height: CELL_SIZE,
            backgroundColor: color,
            borderRadius: '2px',
            cursor: hasMatch ? 'pointer' : 'default',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '8px',
            '&:hover': {
              outline: '1px solid #1b1f23',
              outlineOffset: '-1px'
            }
          }}
        >
          {isDuck && '🦆'}
        </Box>
      </Tooltip>
    );
  };

  // Render a column (week)
  const renderWeek = (weekStart, weekIndex) => {
    const days = [];
    const currentDate = new Date(weekStart);
    
    for (let i = 0; i < 7; i++) {
      const date = new Date(currentDate);
      date.setDate(date.getDate() + i);
      
      // Only render if date is within range
      const dateKey = formatDateKey(date);
      const startKey = dateRange.start;
      const endKey = dateRange.end;
      
      if (dateKey >= startKey && dateKey <= endKey) {
        days.push(renderCell(date));
      } else {
        // Empty placeholder for dates outside range
        days.push(
          <Box
            key={`empty-${weekIndex}-${i}`}
            sx={{
              width: CELL_SIZE,
              height: CELL_SIZE,
            }}
          />
        );
      }
    }
    
    return (
      <Box
        key={weekIndex}
        sx={{
          display: 'flex',
          flexDirection: 'column',
          gap: `${CELL_GAP}px`
        }}
      >
        {days}
      </Box>
    );
  };

  // Calculate stats for the legend
  const stats = useMemo(() => {
    const matchCount = innings.length;
    const totalFantasy = innings.reduce((sum, i) => sum + (i.fantasy_points || 0), 0);
    const avgFantasy = matchCount > 0 ? totalFantasy / matchCount : 0;
    const duckCount = mode === 'batter' 
      ? innings.filter(i => i.runs === 0).length 
      : 0;
    
    return { matchCount, avgFantasy, duckCount };
  }, [innings, mode]);

  if (!dateRange?.start || !dateRange?.end) {
    return null;
  }

  return (
    <Paper elevation={1} sx={{ p: 2, overflow: 'hidden' }}>
      <Typography variant="h6" gutterBottom>
        Performance Graph
      </Typography>
      
      {/* Stats summary */}
      <Box sx={{ mb: 2, display: 'flex', gap: 3, flexWrap: 'wrap' }}>
        <Typography variant="body2" color="text.secondary">
          {stats.matchCount} innings
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Avg Fantasy: {stats.avgFantasy.toFixed(1)}
        </Typography>
        {mode === 'batter' && stats.duckCount > 0 && (
          <Typography variant="body2" color="text.secondary">
            🦆 {stats.duckCount} duck{stats.duckCount > 1 ? 's' : ''}
          </Typography>
        )}
      </Box>

      {/* Graph container with horizontal scroll */}
      <Box sx={{ overflowX: 'auto', pb: 1 }}>
        {/* Month labels */}
        <Box sx={{ display: 'flex', ml: '30px', mb: '4px' }}>
          {monthLabels.map((label, index) => (
            <Typography
              key={index}
              variant="caption"
              sx={{
                width: label.colSpan * (CELL_SIZE + CELL_GAP),
                fontSize: '10px',
                color: 'text.secondary'
              }}
            >
              {label.month}
            </Typography>
          ))}
        </Box>

        {/* Main graph area */}
        <Box sx={{ display: 'flex' }}>
          {/* Day labels */}
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              gap: `${CELL_GAP}px`,
              mr: '4px',
              width: '26px'
            }}
          >
            {DAY_LABELS.map((label, index) => (
              <Typography
                key={index}
                variant="caption"
                sx={{
                  height: CELL_SIZE,
                  fontSize: '9px',
                  color: 'text.secondary',
                  display: 'flex',
                  alignItems: 'center'
                }}
              >
                {label}
              </Typography>
            ))}
          </Box>

          {/* Weeks grid */}
          <Box sx={{ display: 'flex', gap: `${CELL_GAP}px` }}>
            {weeks.map((week, index) => renderWeek(week, index))}
          </Box>
        </Box>
      </Box>

      {/* Legend */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 2 }}>
        <Typography variant="caption" color="text.secondary">Less</Typography>
        {['#ebedf0', '#9be9a8', '#40c463', '#30a14e', '#216e39'].map((color, i) => (
          <Box
            key={i}
            sx={{
              width: CELL_SIZE,
              height: CELL_SIZE,
              backgroundColor: color,
              borderRadius: '2px'
            }}
          />
        ))}
        <Typography variant="caption" color="text.secondary">More</Typography>
        {mode === 'batter' && (
          <Box sx={{ ml: 2, display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Box
              sx={{
                width: CELL_SIZE,
                height: CELL_SIZE,
                backgroundColor: '#ebedf0',
                borderRadius: '2px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '8px'
              }}
            >
              🦆
            </Box>
            <Typography variant="caption" color="text.secondary">Duck</Typography>
          </Box>
        )}
      </Box>
    </Paper>
  );
};

export default ContributionGraph;
