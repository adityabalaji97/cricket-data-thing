import React, { useState } from 'react';
import { 
    Box, 
    Card, 
    Typography, 
    Slider,
    Stack,
    FormControl,
    InputLabel,
    Select,
    MenuItem
} from '@mui/material';
import { 
    ScatterChart,
    Scatter,
    XAxis,
    YAxis,
    Tooltip,
    ResponsiveContainer,
    ReferenceLine,
    ReferenceArea
} from 'recharts';

const BattingScatterChart = ({ data, isMobile = false }) => {
    const [minInnings, setMinInnings] = useState(5);
    const [phase, setPhase] = useState('overall');
    const [plotType, setPlotType] = useState('avgsr');
    
    const phases = [
        { value: 'overall', label: 'Overall' },
        { value: 'pp', label: 'Powerplay' },
        { value: 'middle', label: 'Middle Overs' },
        { value: 'death', label: 'Death Overs' }
    ];

    const plotTypes = [
        { value: 'avgsr', label: 'Average vs Strike Rate' },
        { value: 'dotbound', label: 'Dot% vs Boundary%' }
    ];
    
    const getAxesData = () => {
        const phasePrefix = phase === 'overall' ? '' : `${phase}_`;
        if (plotType === 'avgsr') {
            return {
                xKey: `${phasePrefix}avg`,
                yKey: `${phasePrefix}sr`,
                xLabel: 'Average',
                yLabel: 'Strike Rate'
            };
        }
        return {
            xKey: `${phasePrefix}dot_percent`,
            yKey: `${phasePrefix}boundary_percent`,
            xLabel: 'Dot Ball %',
            yLabel: 'Boundary %'
        };
    };

    const CustomTooltip = ({ active, payload }) => {
        if (active && payload && payload[0]) {
            const data = payload[0].payload;
            const phasePrefix = phase === 'overall' ? '' : `${phase}_`;
            const phaseInnings = phase === 'overall' ? data.innings : 
                data[`${phasePrefix}innings`] || 0;
            const phaseRuns = phase === 'overall' ? data.total_runs : 
                data[`${phasePrefix}runs`] || 0;
            const avg = data[`${phasePrefix}avg`];
            const sr = data[`${phasePrefix}sr`];
            const dotPercent = data[`${phasePrefix}dot_percent`];
            const boundaryPercent = data[`${phasePrefix}boundary_percent`];
    
            return (
                <Box sx={{ bgcolor: 'white', p: 2, border: '1px solid #ccc', borderRadius: 1 }}>
                    <Typography variant="subtitle2">{data.name}</Typography>
                    <Typography variant="body2">
                        {`${phaseRuns} runs in ${phaseInnings} innings`}
                    </Typography>
                    {plotType === 'avgsr' ? (
                        <>
                            <Typography variant="body2">
                                Average: {avg?.toFixed(2) || 'N/A'}
                            </Typography>
                            <Typography variant="body2">
                                Strike Rate: {sr?.toFixed(2) || 'N/A'}
                            </Typography>
                        </>
                    ) : (
                        <>
                            <Typography variant="body2">
                                Dot %: {dotPercent?.toFixed(2) || 'N/A'}
                            </Typography>
                            <Typography variant="body2">
                                Boundary %: {boundaryPercent?.toFixed(2) || 'N/A'}
                            </Typography>
                        </>
                    )}
                </Box>
            );
        }
        return null;
    };
    
    if (!data || data.length === 0) return <div>No data available</div>;

    const avgBatter = data.find(d => d.name === 'Average Batter');
    if (!avgBatter) return <div>Average batter data not found</div>;

    const getTeamColor = (team) => {
        const teamColors = {
            'CSK': '#eff542',
            'RCB': '#f54242', 
            'MI': '#42a7f5',
            'RR': '#FF2AA8',
            'KKR': '#610048',
            'PBKS': '#FF004D',
            'SRH': '#FF7C01',
            'LSG': '#00BBB3',
            'DC': '#004BC5',
            'GT': '#01295B'
        };
        const currentTeam = team?.split('/')?.pop()?.trim();
        return teamColors[currentTeam] || '#000000';
    };

    // Filter data based on minimum innings and phase
    const filteredData = data
        .filter(d => {
            const phasePrefix = phase === 'overall' ? '' : `${phase}_`;
            const phaseInnings = phase === 'overall' ? 
                d.innings : 
                d[`${phasePrefix}innings`] || 0;
            return d.name !== 'Average Batter' && phaseInnings >= minInnings;
        })
        .map(d => ({
            ...d,
            fill: getTeamColor(d.batting_team)
        }))
        // Sort players by total runs (descending) to show the most prolific batters
        .sort((a, b) => {
            const phasePrefix = phase === 'overall' ? '' : `${phase}_`;
            const aRuns = phase === 'overall' ? a.total_runs : a[`${phasePrefix}runs`] || 0;
            const bRuns = phase === 'overall' ? b.total_runs : b[`${phasePrefix}runs`] || 0;
            return bRuns - aRuns; // Descending order
        });

    const metrics = getAxesData();
    
    // Calculate domain boundaries from the filtered data
    const axisData = filteredData.length > 0 
        ? filteredData.map(d => ({
            x: d[metrics.xKey],
            y: d[metrics.yKey]
          }))
        : [{x: 0, y: 0}]; // Default if no data
    
    // Add Average Batter data point to ensure it's included in the domain
    if (avgBatter) {
        axisData.push({
            x: avgBatter[metrics.xKey],
            y: avgBatter[metrics.yKey]
        });
    }
    
    const padding = 0.1; // Increase padding to create more space
    
    // Calculate min/max values safely with fallbacks
    const allXValues = axisData.map(d => d.x).filter(val => !isNaN(val) && val !== undefined);
    const allYValues = axisData.map(d => d.y).filter(val => !isNaN(val) && val !== undefined);
    
    const minX = allXValues.length > 0 ? Math.floor(Math.min(...allXValues) * (1 - padding)) : 0;
    const maxX = allXValues.length > 0 ? Math.ceil(Math.max(...allXValues) * (1 + padding)) : 50;
    const minY = allYValues.length > 0 ? Math.floor(Math.min(...allYValues) * (1 - padding)) : 0;
    const maxY = allYValues.length > 0 ? Math.ceil(Math.max(...allYValues) * (1 + padding)) : 150;

    return (
        <Card sx={{ width: '100%', p: 2, pb: 0 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>
                Batting Performance Analysis
            </Typography>
            
            <Stack 
                direction={isMobile ? "column" : "row"} 
                spacing={isMobile ? 3 : 2} 
                alignItems="stretch" 
                sx={{ 
                    mb: 2,
                    width: '100%'
                }}
            >
                <Box sx={{ width: '100%' }}>
                    <Typography variant="body2" gutterBottom>
                        Minimum Innings: {minInnings} ({filteredData.length} players)
                    </Typography>
                    <Slider
                        value={minInnings}
                        onChange={(_, value) => setMinInnings(value)}
                        min={1}
                        max={15}
                        step={1}
                        marks
                        aria-label="Minimum Innings"
                        valueLabelDisplay="auto"
                    />
                </Box>
                <FormControl sx={{ width: '100%' }}>
                    <InputLabel>Phase</InputLabel>
                    <Select
                        value={phase}
                        onChange={(e) => setPhase(e.target.value)}
                        label="Phase"
                        fullWidth
                    >
                        {phases.map(p => (
                            <MenuItem key={p.value} value={p.value}>{p.label}</MenuItem>
                        ))}
                    </Select>
                </FormControl>
                <FormControl sx={{ width: '100%' }}>
                    <InputLabel>Plot Type</InputLabel>
                    <Select
                        value={plotType}
                        onChange={(e) => setPlotType(e.target.value)}
                        label="Plot Type"
                        fullWidth
                    >
                        {plotTypes.map(p => (
                            <MenuItem key={p.value} value={p.value}>{p.label}</MenuItem>
                        ))}
                    </Select>
                </FormControl>
            </Stack>

            <Box sx={{ width: '100%', height: 520, mt: 2, mb: 0 }}>
                <ResponsiveContainer>
                    <ScatterChart margin={{ top: 10, right: 20, bottom: 0, left: 0 }}>
                        {plotType === 'avgsr' ? (
                            <>
                                <ReferenceArea
                                    x1={avgBatter[metrics.xKey]}
                                    x2={maxX}
                                    y1={avgBatter[metrics.yKey]}
                                    y2={maxY}
                                    fill="#77DD77"
                                    fillOpacity={0.3}
                                />
                                <ReferenceArea
                                    x1={avgBatter[metrics.xKey]}
                                    x2={maxX}
                                    y1={minY}
                                    y2={avgBatter[metrics.yKey]}
                                    fill="#FFB347"
                                    fillOpacity={0.3}
                                />
                                <ReferenceArea
                                    x1={minX}
                                    x2={avgBatter[metrics.xKey]}
                                    y1={avgBatter[metrics.yKey]}
                                    y2={maxY}
                                    fill="#FFB347"
                                    fillOpacity={0.3}
                                />
                                <ReferenceArea
                                    x1={minX}
                                    x2={avgBatter[metrics.xKey]}
                                    y1={minY}
                                    y2={avgBatter[metrics.yKey]}
                                    fill="#FF6961"
                                    fillOpacity={0.3}
                                />
                            </>
                        ) : (
                            <>
                                <ReferenceArea
                                    x1={minX}
                                    x2={avgBatter[metrics.xKey]}
                                    y1={avgBatter[metrics.yKey]}
                                    y2={maxY}
                                    fill="#77DD77"
                                    fillOpacity={0.3}
                                />
                                <ReferenceArea
                                    x1={minX}
                                    x2={avgBatter[metrics.xKey]}
                                    y1={minY}
                                    y2={avgBatter[metrics.yKey]}
                                    fill="#FFB347"
                                    fillOpacity={0.3}
                                />
                                <ReferenceArea
                                    x1={avgBatter[metrics.xKey]}
                                    x2={maxX}
                                    y1={avgBatter[metrics.yKey]}
                                    y2={maxY}
                                    fill="#FFB347"
                                    fillOpacity={0.3}
                                />
                                <ReferenceArea
                                    x1={avgBatter[metrics.xKey]}
                                    x2={maxX}
                                    y1={minY}
                                    y2={avgBatter[metrics.yKey]}
                                    fill="#FF6961"
                                    fillOpacity={0.3}
                                />
                            </>
                        )}
                        <XAxis 
                            type="number" 
                            dataKey={metrics.xKey}
                            domain={[minX, maxX]}
                            axisLine={{ strokeWidth: 1 }}
                            tickSize={4}
                            dy={0}
                            padding={{ left: 0, right: 0, top: 0, bottom: 0 }}
                        />
                        <YAxis 
                            type="number" 
                            dataKey={metrics.yKey}
                            domain={[minY, maxY]}
                            axisLine={{ strokeWidth: 1 }}
                            tickSize={4}
                            dx={0}
                            padding={{ left: 0, right: 0, top: 0, bottom: 0 }}
                        />
                        
                        <ReferenceLine x={avgBatter[metrics.xKey]} stroke="#666" strokeDasharray="3 3" />
                        <ReferenceLine y={avgBatter[metrics.yKey]} stroke="#666" strokeDasharray="3 3" />

                        <Tooltip content={<CustomTooltip />} />

                        <Scatter
                            name="Players"
                            data={filteredData.length > 30 ? filteredData.slice(0, 30) : filteredData}
                            fill="#8884d8"
                            shape={(props) => {
                                const { cx, cy, fill, payload } = props;
                                return (
                                    <>
                                        <circle
                                            cx={cx}
                                            cy={cy}
                                            r={6}
                                            fill={fill || '#8884d8'}
                                            stroke="#fff"
                                            strokeWidth={1}
                                        />
                                        <text
                                            x={cx}
                                            y={cy + 15}
                                            textAnchor="middle"
                                            fontSize={12}
                                            fill="#000"
                                        >
                                            {payload.name.length > 8 ? payload.name.substring(0, 8) + '...' : payload.name}
                                        </text>
                                    </>
                                );
                            }}
                        />
                        
                        <Scatter
                            name="Average Batter"
                            data={[avgBatter]}
                            fill="#000"
                            shape={(props) => {
                                const { cx, cy } = props;
                                return (
                                    <>
                                        <polygon
                                            points={`${cx},${cy-8} ${cx+8},${cy} ${cx},${cy+8} ${cx-8},${cy}`}
                                            fill="#000"
                                            stroke="#fff"
                                            strokeWidth={1}
                                        />
                                        <text
                                            x={cx}
                                            y={cy + 20}
                                            textAnchor="middle"
                                            fontSize={11}
                                            fontWeight="bold"
                                            fill="#000"
                                        >
                                            Avg. Batter
                                        </text>
                                    </>
                                );
                            }}
                        />
                    </ScatterChart>
                </ResponsiveContainer>
            </Box>
        </Card>
    );
};

export default BattingScatterChart;