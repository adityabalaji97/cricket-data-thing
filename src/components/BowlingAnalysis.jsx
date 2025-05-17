import React, { useState, useEffect } from 'react';
import { 
    Box, 
    Typography, 
    Stack,
    ToggleButton,
    ToggleButtonGroup
} from '@mui/material';
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer
} from 'recharts';
import axios from 'axios';
import config from '../config';

const BowlingAnalysis = ({ 
    venue,
    startDate,
    endDate,
    statsData,
    isMobile
}) => {
    const [selectedPhase, setSelectedPhase] = useState('overall');
    const [selectedMetric, setSelectedMetric] = useState('ballsPercentage');
    const [bowlingData, setBowlingData] = useState(null);
    const [loading, setLoading] = useState(false);

    const metrics = {
        ballsPercentage: { label: '% BALLS BOWLED', key: 'ballsPercentage' },
        wicketsPercentage: { label: '% WICKETS TAKEN', key: 'wicketsPercentage' },
        dotBallPercentage: { label: 'DOT BALL %', key: 'dotBallPercentage' },
        boundaryPercentage: { label: 'BOUNDARY %', key: 'boundaryPercentage' },
        economyRate: { label: 'ECONOMY RATE', key: 'economyRate' },
        strikeRate: { label: 'STRIKE RATE', key: 'strikeRate' },
        average: { label: 'BOWLING AVERAGE', key: 'average' }
    };

    const phases = {
        pp: 'POWER PLAY',
        middle: 'MIDDLE OVERS',
        death: 'DEATH OVERS',
        overall: 'OVERALL'
    };

    useEffect(() => {
      const fetchBowlingData = async () => {
          try {
              setLoading(true);
              const params = new URLSearchParams();
              params.append('start_date', startDate);
              params.append('end_date', endDate);
              params.append('venue', venue);
  
              try {
                    const response = await axios.get(`${config.API_URL}/venue-bowling-stats?${params.toString()}`);
                    setBowlingData(response.data);
              } catch (error) {
                  console.error('Error fetching bowling data:', error);
                  // Provide default data structure if API fails
                  setBowlingData({
                      paceVsSpin: {
                          pp: { pace: defaultMetrics(), spin: defaultMetrics() },
                          middle: { pace: defaultMetrics(), spin: defaultMetrics() },
                          death: { pace: defaultMetrics(), spin: defaultMetrics() },
                          overall: { pace: defaultMetrics(), spin: defaultMetrics() }
                      },
                      bowlingTypes: {
                          pp: [],
                          middle: [],
                          death: [],
                          overall: []
                      }
                  });
              }
          } catch (error) {
              console.error('General error in fetchBowlingData:', error);
          } finally {
              setLoading(false);
          }
      };
      
      // Helper function to create default metrics
      const defaultMetrics = () => ({
          ballsPercentage: 0,
          wicketsPercentage: 0,
          dotBallPercentage: 0,
          boundaryPercentage: 0,
          economyRate: 0,
          strikeRate: 0,
          average: 0
      });
  
      fetchBowlingData();
  }, [venue, startDate, endDate]);

    if (loading) {
        return <Box sx={{ p: 2 }}>Loading bowling analysis...</Box>;
    }

    return (
        <Box>
            {/* Phase Selection */}
            <Stack 
                direction={{ xs: 'column', md: 'row' }} 
                spacing={2} 
                sx={{ mb: 3 }}
                alignItems="center"
            >
                <ToggleButtonGroup
                    value={selectedPhase}
                    exclusive
                    onChange={(_, value) => value && setSelectedPhase(value)}
                    sx={{ 
                        mb: { xs: 1, md: 2 },
                        flexWrap: 'wrap',
                        '& .MuiToggleButton-root': {
                            px: { xs: 1, md: 2 },
                            py: { xs: 0.5, md: 1 },
                            fontSize: { xs: '0.7rem', md: '0.875rem' }
                        }
                    }}
                >
                    {Object.entries(phases).map(([phase, label]) => (
                        <ToggleButton key={phase} value={phase}>
                            {label}
                        </ToggleButton>
                    ))}
                </ToggleButtonGroup>

                <ToggleButtonGroup
                    value={selectedMetric}
                    exclusive
                    onChange={(_, value) => value && setSelectedMetric(value)}
                    sx={{ 
                        flexWrap: 'wrap',
                        '& .MuiToggleButton-root': {
                            px: { xs: 1, md: 2 },
                            py: { xs: 0.5, md: 1 },
                            fontSize: { xs: '0.7rem', md: '0.875rem' }
                        }
                    }}
                >
                    {Object.entries(metrics).map(([key, { label }]) => (
                        <ToggleButton key={key} value={key}>
                            {label}
                        </ToggleButton>
                    ))}
                </ToggleButtonGroup>
            </Stack>

            {/* Charts */}
            {bowlingData && (
                <Stack spacing={isMobile ? 2 : 3}>
                    {/* Pace vs Spin Overview */}
                    <Box>
                        <Typography variant={isMobile ? "subtitle1" : "h6"} gutterBottom>
                            Pace vs Spin Comparison
                        </Typography>
                        <Box sx={{ height: isMobile ? 300 : 400 }}>
                            <ResponsiveContainer>
                                <BarChart
                                    data={[
                                        {
                                            type: 'Pace',
                                            value: bowlingData?.paceVsSpin?.[selectedPhase]?.pace?.[metrics[selectedMetric].key] || 0
                                        },
                                        {
                                            type: 'Spin',
                                            value: bowlingData?.paceVsSpin?.[selectedPhase]?.spin?.[metrics[selectedMetric].key] || 0
                                        }
                                    ]}
                                >
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis dataKey="type" tick={{ fontSize: isMobile ? 10 : 12 }} />
                                    <YAxis tick={{ fontSize: isMobile ? 10 : 12 }} />
                                    <Tooltip 
                                        formatter={(value) => {
                                            if (selectedMetric.includes('Percentage')) {
                                                return `${value.toFixed(1)}%`;
                                            } else if (selectedMetric === 'economyRate') {
                                                return `${value.toFixed(2)} runs/over`;
                                            } else if (selectedMetric === 'strikeRate') {
                                                return `${value.toFixed(1)} balls/wicket`;
                                            } else {
                                                return `${value.toFixed(2)}`;
                                            }
                                        }}
                                    />
                                    <Legend />
                                    <Bar 
                                        dataKey="value" 
                                        fill="#8884d8"
                                        label={isMobile ? false : {
                                            position: 'top',
                                            formatter: (value) => value.toFixed(1)
                                        }}
                                    />
                                </BarChart>
                            </ResponsiveContainer>
                        </Box>
                    </Box>

                    {/* Detailed Bowling Types */}
                    <Box>
                        <Typography variant={isMobile ? "subtitle1" : "h6"} gutterBottom>
                            Bowling Type Breakdown
                        </Typography>
                        <Box sx={{ height: isMobile ? 300 : 400 }}>
                            <ResponsiveContainer>
                                <BarChart
                                    data={bowlingData?.bowlingTypes?.[selectedPhase] || []}
                                >
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis dataKey="bowlingType" tick={{ fontSize: isMobile ? 10 : 12 }} />
                                    <YAxis tick={{ fontSize: isMobile ? 10 : 12 }} />
                                    <Tooltip 
                                        formatter={(value) => {
                                            if (selectedMetric.includes('Percentage')) {
                                                return `${value.toFixed(1)}%`;
                                            } else if (selectedMetric === 'economyRate') {
                                                return `${value.toFixed(2)} runs/over`;
                                            } else if (selectedMetric === 'strikeRate') {
                                                return `${value.toFixed(1)} balls/wicket`;
                                            } else {
                                                return `${value.toFixed(2)}`;
                                            }
                                        }}
                                    />
                                    <Legend />
                                    <Bar 
                                        dataKey={metrics[selectedMetric].key} 
                                        fill="#82ca9d"
                                        label={isMobile ? false : {
                                            position: 'top',
                                            formatter: (value) => value.toFixed(1)
                                        }}
                                    />
                                </BarChart>
                            </ResponsiveContainer>
                        </Box>
                    </Box>
                </Stack>
            )}
        </Box>
    );
};

export default BowlingAnalysis;