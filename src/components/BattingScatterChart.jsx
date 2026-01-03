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
        { value: 'middle', label: isMobile ? 'Middle' : 'Middle Overs' },
        { value: 'death', label: isMobile ? 'Death' : 'Death Overs' }
    ];

    const plotTypes = [
        { value: 'avgsr', label: isMobile ? 'Avg vs SR' : 'Average vs Strike Rate' },
        { value: 'dotbound', label: isMobile ? 'Dot vs Bnd' : 'Dot% vs Boundary%' }
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
                <Box sx={{ bgcolor: 'white', p: isMobile ? 1 : 2, border: '1px solid #ccc', borderRadius: 1 }}>
                    <Typography variant="subtitle2" sx={{ fontSize: isMobile ? '0.75rem' : '0.875rem', fontWeight: 600 }}>
                        {data.name}
                    </Typography>
                    <Typography variant="body2" sx={{ fontSize: isMobile ? '0.7rem' : '0.75rem' }}>
                        {`${phaseRuns} runs in ${phaseInnings} innings`}
                    </Typography>
                    {plotType === 'avgsr' ? (
                        <>
                            <Typography variant="body2" sx={{ fontSize: isMobile ? '0.7rem' : '0.75rem' }}>
                                Average: {avg?.toFixed(2) || 'N/A'}
                            </Typography>
                            <Typography variant="body2" sx={{ fontSize: isMobile ? '0.7rem' : '0.75rem' }}>
                                Strike Rate: {sr?.toFixed(2) || 'N/A'}
                            </Typography>
                        </>
                    ) : (
                        <>
                            <Typography variant="body2" sx={{ fontSize: isMobile ? '0.7rem' : '0.75rem' }}>
                                Dot %: {dotPercent?.toFixed(2) || 'N/A'}
                            </Typography>
                            <Typography variant="body2" sx={{ fontSize: isMobile ? '0.7rem' : '0.75rem' }}>
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

    // Limit number of players shown on mobile to reduce crowding
    const maxPlayers = isMobile ? 15 : 30;
    const displayData = filteredData.slice(0, maxPlayers);

    const metrics = getAxesData();

    // Calculate domain boundaries from the display data
    const axisData = displayData.length > 0
        ? displayData.map(d => ({
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

    // Responsive height calculation - fits in mobile viewport for screenshots
    const chartHeight = isMobile ?
        Math.min(typeof window !== 'undefined' ? window.innerHeight * 0.65 : 450, 500) :
        520;

    return (
        <Card sx={{
            width: '100%',
            p: isMobile ? 1.5 : 2,
            pb: 0,
            backgroundColor: isMobile ? 'transparent' : undefined,
            boxShadow: isMobile ? 0 : undefined
        }}>
            <Typography variant={isMobile ? "body1" : "h6"} sx={{ mb: isMobile ? 1 : 2, fontWeight: 600 }}>
                Batting Performance Analysis
            </Typography>

            {filteredData.length > maxPlayers && (
                <Typography variant="caption" sx={{ display: 'block', color: 'text.secondary', mb: 1, fontSize: isMobile ? '0.65rem' : '0.75rem' }}>
                    Showing top {maxPlayers} players by runs (from {filteredData.length} total)
                </Typography>
            )}

            <Stack
                direction="column"
                spacing={isMobile ? 1 : 2}
                sx={{ mb: isMobile ? 1 : 2 }}
            >
                <Box sx={{ width: '100%' }}>
                    <Typography variant="body2" gutterBottom sx={{ fontSize: isMobile ? '0.7rem' : '0.875rem' }}>
                        Min Innings: {minInnings} ({filteredData.length} players)
                    </Typography>
                    <Slider
                        value={minInnings}
                        onChange={(_, value) => setMinInnings(value)}
                        min={1}
                        max={15}
                        step={1}
                        marks={!isMobile}
                        aria-label="Minimum Innings"
                        valueLabelDisplay="auto"
                        size={isMobile ? "small" : "medium"}
                    />
                </Box>
                <Stack direction="row" spacing={isMobile ? 1 : 2} sx={{ width: '100%' }}>
                    <FormControl sx={{ flex: 1 }} size={isMobile ? "small" : "medium"}>
                        <InputLabel sx={{ fontSize: isMobile ? '0.75rem' : '1rem' }}>Phase</InputLabel>
                        <Select
                            value={phase}
                            onChange={(e) => setPhase(e.target.value)}
                            label="Phase"
                            sx={{ fontSize: isMobile ? '0.75rem' : '1rem' }}
                        >
                            {phases.map(p => (
                                <MenuItem key={p.value} value={p.value} sx={{ fontSize: isMobile ? '0.75rem' : '1rem' }}>
                                    {p.label}
                                </MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                    <FormControl sx={{ flex: 1 }} size={isMobile ? "small" : "medium"}>
                        <InputLabel sx={{ fontSize: isMobile ? '0.75rem' : '1rem' }}>Plot Type</InputLabel>
                        <Select
                            value={plotType}
                            onChange={(e) => setPlotType(e.target.value)}
                            label="Plot Type"
                            sx={{ fontSize: isMobile ? '0.75rem' : '1rem' }}
                        >
                            {plotTypes.map(p => (
                                <MenuItem key={p.value} value={p.value} sx={{ fontSize: isMobile ? '0.75rem' : '1rem' }}>
                                    {p.label}
                                </MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                </Stack>
            </Stack>

            <Box sx={{ width: '100%', height: chartHeight, mt: isMobile ? 1 : 2, mb: 0 }}>
                <ResponsiveContainer>
                    <ScatterChart margin={{
                        top: 10,
                        right: isMobile ? 10 : 20,
                        bottom: 0,
                        left: isMobile ? -10 : 0
                    }}>
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
                            tick={{ fontSize: isMobile ? 9 : 12 }}
                        />
                        <YAxis
                            type="number"
                            dataKey={metrics.yKey}
                            domain={[minY, maxY]}
                            axisLine={{ strokeWidth: 1 }}
                            tickSize={4}
                            dx={0}
                            padding={{ left: 0, right: 0, top: 0, bottom: 0 }}
                            tick={{ fontSize: isMobile ? 9 : 12 }}
                        />

                        <ReferenceLine x={avgBatter[metrics.xKey]} stroke="#666" strokeDasharray="3 3" />
                        <ReferenceLine y={avgBatter[metrics.yKey]} stroke="#666" strokeDasharray="3 3" />

                        <Tooltip content={<CustomTooltip />} />

                        <Scatter
                            name="Players"
                            data={displayData}
                            fill="#8884d8"
                            shape={(props) => {
                                const { cx, cy, fill, payload } = props;
                                // Extract last name for label
                                const nameParts = payload.name?.split(' ') || [];
                                const label = nameParts.length > 1
                                    ? nameParts[nameParts.length - 1]
                                    : nameParts[0] || '';

                                return (
                                    <g>
                                        <circle
                                            cx={cx}
                                            cy={cy}
                                            r={isMobile ? 8 : 6}
                                            fill={fill || '#8884d8'}
                                            stroke="#fff"
                                            strokeWidth={isMobile ? 1.5 : 1}
                                        />
                                        <text
                                            x={cx}
                                            y={cy + (isMobile ? 16 : 18)}
                                            textAnchor="middle"
                                            fill="#333"
                                            fontSize={isMobile ? 7 : 8}
                                            fontWeight="600"
                                        >
                                            {label}
                                        </text>
                                    </g>
                                );
                            }}
                        />

                        <Scatter
                            name="Average Batter"
                            data={[avgBatter]}
                            fill="#000"
                            shape={(props) => {
                                const { cx, cy } = props;
                                const size = isMobile ? 9 : 8;
                                return (
                                    <polygon
                                        points={`${cx},${cy-size} ${cx+size},${cy} ${cx},${cy+size} ${cx-size},${cy}`}
                                        fill="#000"
                                        stroke="#fff"
                                        strokeWidth={1.5}
                                    />
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