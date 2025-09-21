import React, { useState, useRef } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Tabs,
  Tab,
  Divider
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import ChartPanel from './ChartPanel';

const TeamComparisonVisualization = ({ teams, showPercentiles }) => {
  const battingChartPanelRef = useRef(null);
  const bowlingChartPanelRef = useRef(null);
  
  const [showBattingCharts, setShowBattingCharts] = useState(false);
  const [showBowlingCharts, setShowBowlingCharts] = useState(false);
  
  const [selectedPhase, setSelectedPhase] = useState('powerplay');
  const [currentTab, setCurrentTab] = useState(0);

  if (!teams || teams.length === 0) {
    return null;
  }

  const phases = [
    { key: 'powerplay', label: 'Powerplay (1-6)' },
    { key: 'middle_overs', label: 'Middle Overs (7-15)' },
    { key: 'death_overs', label: 'Death Overs (16-20)' }
  ];

  const tabs = [
    { label: 'Batting Performance', key: 'batting' },
    { label: 'Bowling Performance', key: 'bowling' }
  ];

  // Prepare batting performance data for the selected phase
  const prepareBattingData = () => {
    const chartData = [];
    
    teams.forEach(team => {
      if (team.phaseStats && team.phaseStats[selectedPhase]) {
        const stats = team.phaseStats[selectedPhase];
        if (stats && typeof stats === 'object') {
          chartData.push({
            team: team.label,
            phase: selectedPhase,
            runs: showPercentiles ? (stats.normalized_runs || stats.runs) : (stats.runs || 0),
            balls: stats.balls || 0,
            wickets: stats.wickets || 0,
            average: showPercentiles ? (stats.normalized_average || stats.average) : (stats.average || 0),
            strike_rate: showPercentiles ? (stats.normalized_strike_rate || stats.strike_rate) : (stats.strike_rate || 0),
            ...stats
          });
        }
      }
    });
    
    return chartData;
  };

  // Prepare bowling performance data for the selected phase
  const prepareBowlingData = () => {
    const chartData = [];
    
    teams.forEach(team => {
      if (team.bowlingPhaseStats && team.bowlingPhaseStats[selectedPhase]) {
        const stats = team.bowlingPhaseStats[selectedPhase];
        if (stats && typeof stats === 'object') {
          chartData.push({
            team: team.label,
            phase: selectedPhase,
            runs: stats.runs || 0,
            balls: stats.balls || 0,
            wickets: stats.wickets || 0,
            bowling_average: showPercentiles ? (stats.normalized_average || stats.bowling_average) : (stats.bowling_average || 0),
            bowling_strike_rate: showPercentiles ? (stats.normalized_strike_rate || stats.bowling_strike_rate) : (stats.bowling_strike_rate || 0),
            economy_rate: showPercentiles ? (stats.normalized_economy || stats.economy_rate) : (stats.economy_rate || 0),
            // Also add with generic names for easier charting
            average: showPercentiles ? (stats.normalized_average || stats.bowling_average) : (stats.bowling_average || 0),
            strike_rate: showPercentiles ? (stats.normalized_strike_rate || stats.bowling_strike_rate) : (stats.bowling_strike_rate || 0),
            economy: showPercentiles ? (stats.normalized_economy || stats.economy_rate) : (stats.economy_rate || 0),
            ...stats
          });
        }
      }
    });
    
    return chartData;
  };

  // Chart management functions
  const handleAddBattingBarChart = () => {
    setShowBattingCharts(true);
    setTimeout(() => {
      if (battingChartPanelRef.current && battingChartPanelRef.current.addBarChart) {
        battingChartPanelRef.current.addBarChart();
      }
    }, 100);
  };

  const handleAddBattingScatterChart = () => {
    setShowBattingCharts(true);
    setTimeout(() => {
      if (battingChartPanelRef.current && battingChartPanelRef.current.addScatterChart) {
        battingChartPanelRef.current.addScatterChart();
      }
    }, 100);
  };

  const handleAddBowlingBarChart = () => {
    setShowBowlingCharts(true);
    setTimeout(() => {
      if (bowlingChartPanelRef.current && bowlingChartPanelRef.current.addBarChart) {
        bowlingChartPanelRef.current.addBarChart();
      }
    }, 100);
  };

  const handleAddBowlingScatterChart = () => {
    setShowBowlingCharts(true);
    setTimeout(() => {
      if (bowlingChartPanelRef.current && bowlingChartPanelRef.current.addScatterChart) {
        bowlingChartPanelRef.current.addScatterChart();
      }
    }, 100);
  };

  // Get data based on current tab
  const getCurrentData = () => {
    switch (currentTab) {
      case 0: return prepareBattingData();
      case 1: return prepareBowlingData();
      default: return [];
    }
  };

  const currentData = getCurrentData();

  return (
    <Box sx={{ mt: 4 }}>
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            📊 Generate Visualizations
          </Typography>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Create charts for each data table. Choose the table type and add multiple charts with full customization.
          </Typography>

          {/* Tab Selection */}
          <Box sx={{ mt: 3 }}>
            <Tabs 
              value={currentTab} 
              onChange={(e, newValue) => setCurrentTab(newValue)}
              variant="scrollable"
              scrollButtons="auto"
            >
              {tabs.map((tab, index) => (
                <Tab key={tab.key} label={tab.label} />
              ))}
            </Tabs>
          </Box>

          <Divider sx={{ my: 3 }} />

          {/* Phase Selector */}
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={12} sm={6} md={4}>
              <FormControl fullWidth size="small">
                <InputLabel>Select Phase</InputLabel>
                <Select
                  value={selectedPhase}
                  onChange={(e) => setSelectedPhase(e.target.value)}
                  label="Select Phase"
                >
                  {phases.map(phase => (
                    <MenuItem key={phase.key} value={phase.key}>
                      {phase.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
          </Grid>

          {/* Chart Buttons */}
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} md={4}>
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                onClick={() => {
                  switch (currentTab) {
                    case 0: handleAddBattingBarChart(); break;
                    case 1: handleAddBowlingBarChart(); break;
                  }
                }}
                fullWidth
                disabled={currentData.length === 0}
              >
                Add Bar Chart
              </Button>
            </Grid>
            
            <Grid item xs={12} sm={6} md={4}>
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                onClick={() => {
                  switch (currentTab) {
                    case 0: handleAddBattingScatterChart(); break;
                    case 1: handleAddBowlingScatterChart(); break;
                  }
                }}
                fullWidth
                disabled={currentData.length === 0}
              >
                Add Scatter Plot
              </Button>
            </Grid>
          </Grid>

          {/* Data Summary */}
          {currentData.length > 0 && (
            <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block' }}>
              Currently showing: {tabs[currentTab].label} | {phases.find(p => p.key === selectedPhase)?.label}
              {showPercentiles ? ' | Percentile values' : ' | Absolute values'} | 
              {currentData.length} data points
            </Typography>
          )}

          {currentData.length === 0 && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 2, fontStyle: 'italic' }}>
              No data available for charting in this category. Make sure teams have been compared first.
            </Typography>
          )}
        </CardContent>
      </Card>

      {/* Batting Performance Charts */}
      {currentTab === 0 && (
        <ChartPanel 
          ref={battingChartPanelRef}
          data={prepareBattingData()}
          groupBy={['team']}
          isVisible={showBattingCharts && prepareBattingData().length > 0}
          onToggle={() => setShowBattingCharts(!showBattingCharts)}
          isMobile={false}
        />
      )}

      {/* Bowling Performance Charts */}
      {currentTab === 1 && (
        <ChartPanel 
          ref={bowlingChartPanelRef}
          data={prepareBowlingData()}
          groupBy={['team']}
          isVisible={showBowlingCharts && prepareBowlingData().length > 0}
          onToggle={() => setShowBowlingCharts(!showBowlingCharts)}
          isMobile={false}
        />
      )}
    </Box>
  );
};

export default TeamComparisonVisualization;