import React, { useState, useEffect } from 'react';
import axios from 'axios';
import config from '../config';
import { 
    Box, 
    Card, 
    Grid, 
    Typography, 
    CircularProgress, 
    Alert,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Slider,
    Stack,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
    Tabs,
    Tab,
    useMediaQuery,
    useTheme,
    Divider
} from '@mui/material';
import { 
    PieChart, 
    Pie, 
    Cell, 
    BarChart, 
    Bar, 
    XAxis, 
    YAxis, 
    ResponsiveContainer, 
    Tooltip,
    ScatterChart,
    Scatter,
    ReferenceLine,
    ReferenceArea,
    Legend
} from 'recharts';
import BowlingAnalysis from './BowlingAnalysis';
import FantasyPointsTable from './FantasyPointsTable';
import FantasyPointsBarChart from './FantasyPointsBarChart';
import MatchHistory from './MatchHistory';
import Matchups from './Matchups';
import BattingScatterChart from './BattingScatterChart';
import ContextualQueryPrompts from './ContextualQueryPrompts';
import { getVenueContextualQueries } from '../utils/queryBuilderLinks';

const BattingScatter = ({ data, isMobile }) => {
    const [minInnings, setMinInnings] = useState(5);
    const [phase, setPhase] = useState('overall');
    const [plotType, setPlotType] = useState('avgsr');

    const phases = [
        { value: 'overall', label: 'Overall' },
        { value: 'pp', label: 'Powerplay' },
        { value: 'middle', label: 'Middle' },
        { value: 'death', label: 'Death' }
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

    if (!data || data.length === 0) return null;

    const avgBatter = data.find(d => d.name === 'Average Batter');
    if (!avgBatter) return null;

    // Responsive height calculation - fits in mobile viewport for screenshots
    const chartHeight = isMobile ?
        Math.min(typeof window !== 'undefined' ? window.innerHeight * 0.65 : 450, 500) :
        650;

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

    // Calculate domain boundaries from the filtered data
    const metrics = getAxesData();

    // Check if filteredData has any elements before mapping
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

    return (
        <Box sx={{ width: '100%', height: chartHeight, display: 'flex', flexDirection: 'column', pt: 0 }}>
            <Typography variant={isMobile ? "body1" : "h6"} sx={{ px: 2, mb: 1, fontWeight: 600 }}>
                Batting Performance Analysis
            </Typography>

            {filteredData.length > maxPlayers && (
                <Typography variant="caption" sx={{ px: 2, display: 'block', color: 'text.secondary', mb: 1, fontSize: isMobile ? '0.65rem' : '0.75rem' }}>
                    Showing top {maxPlayers} players by runs (from {filteredData.length} total)
                </Typography>
            )}

            <Stack
                direction="column"
                spacing={isMobile ? 1 : 2}
                sx={{ px: 2, mb: isMobile ? 1 : 2 }}
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

            <Box sx={{ flex: 1, width: '100%', px: isMobile ? 0 : 1 }}>
                <ResponsiveContainer width="100%" height="100%">
                    <ScatterChart
                        margin={{
                            top: 10,
                            right: isMobile ? 5 : 20,
                            bottom: isMobile ? 20 : 20,
                            left: isMobile ? 0 : 20
                        }}
                    >
                        {plotType === 'avgsr' ? (
                            <>
                                <ReferenceArea
                                    x1={avgBatter[metrics.xKey]}
                                    x2={maxX}
                                    y1={avgBatter[metrics.yKey]}
                                    y2={maxY}
                                    fill="#77DD77"
                                    opacity={0.3}
                                />
                                <ReferenceArea
                                    x1={avgBatter[metrics.xKey]}
                                    x2={maxX}
                                    y1={minY}
                                    y2={avgBatter[metrics.yKey]}
                                    fill="#FFB347"
                                    opacity={0.3}
                                />
                                <ReferenceArea
                                    x1={minX}
                                    x2={avgBatter[metrics.xKey]}
                                    y1={avgBatter[metrics.yKey]}
                                    y2={maxY}
                                    fill="#FFB347"
                                    opacity={0.3}
                                />
                                <ReferenceArea
                                    x1={minX}
                                    x2={avgBatter[metrics.xKey]}
                                    y1={minY}
                                    y2={avgBatter[metrics.yKey]}
                                    fill="#FF6961"
                                    opacity={0.3}
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
                                    opacity={0.3}
                                />
                                <ReferenceArea
                                    x1={minX}
                                    x2={avgBatter[metrics.xKey]}
                                    y1={minY}
                                    y2={avgBatter[metrics.yKey]}
                                    fill="#FFB347"
                                    opacity={0.3}
                                />
                                <ReferenceArea
                                    x1={avgBatter[metrics.xKey]}
                                    x2={maxX}
                                    y1={avgBatter[metrics.yKey]}
                                    y2={maxY}
                                    fill="#FFB347"
                                    opacity={0.3}
                                />
                                <ReferenceArea
                                    x1={avgBatter[metrics.xKey]}
                                    x2={maxX}
                                    y1={minY}
                                    y2={avgBatter[metrics.yKey]}
                                    fill="#FF6961"
                                    opacity={0.3}
                                />
                            </>
                        )}

                        <XAxis
                            type="number"
                            dataKey={metrics.xKey}
                            domain={[minX, maxX]}
                            tick={{ fontSize: isMobile ? 9 : 12 }}
                        />
                        <YAxis
                            type="number"
                            dataKey={metrics.yKey}
                            domain={[minY, maxY]}
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
                                // Extract last name
                                const nameParts = payload.name?.split(' ') || [];
                                const label = nameParts.length > 1
                                    ? nameParts[nameParts.length - 1]
                                    : nameParts[0] || '';

                                return (
                                    <g>
                                        <circle
                                            cx={cx}
                                            cy={cy}
                                            r={isMobile ? 8 : 8}
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
                                const size = isMobile ? 9 : 10;
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
        </Box>
    );
};

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

const BattingLeaders = ({ data, isMobile }) => {
    if (!data || data.length === 0) return null;

    return (
        <TableContainer sx={{ overflowX: 'hidden' }}>
            <Typography variant="h6" gutterBottom align="center">Most Runs</Typography>
            <Table size="small">
                <TableHead>
                    <TableRow>
                        <TableCell sx={{ px: isMobile ? 0.5 : 1 }}>Name</TableCell>
                        <TableCell align="right" sx={{ px: isMobile ? 0.5 : 1 }}>Inns</TableCell>
                        <TableCell align="right" sx={{ px: isMobile ? 0.5 : 1 }}>Runs</TableCell>
                        <TableCell align="right" sx={{ px: isMobile ? 0.5 : 1 }}>Avg @ SR</TableCell>
                        <TableCell align="right" sx={{ px: isMobile ? 0.5 : 1 }}>BPD</TableCell>
                    </TableRow>
                </TableHead>
                <TableBody>
                    {data.map((row, index) => (
                        <TableRow
                            key={`${row.name}-${index}`}
                            sx={{ '&:nth-of-type(odd)': { backgroundColor: 'rgba(0, 0, 0, 0.04)' } }}
                        >
                            <TableCell sx={{ px: isMobile ? 0.5 : 1, fontSize: isMobile ? '0.75rem' : '0.875rem' }}>
                                <Box
                                    component="span"
                                    sx={{
                                        cursor: 'help',
                                        textDecoration: 'underline',
                                        textDecorationStyle: 'dotted'
                                    }}
                                    title={`Teams: ${row.batting_team}`}
                                >
                                    {row.name}
                                </Box>
                            </TableCell>
                            <TableCell align="right" sx={{ px: isMobile ? 0.5 : 1, fontSize: isMobile ? '0.75rem' : '0.875rem' }}>
                                {row.batInns}
                            </TableCell>
                            <TableCell align="right" sx={{ px: isMobile ? 0.5 : 1, fontSize: isMobile ? '0.75rem' : '0.875rem' }}>
                                {row.batRuns}
                            </TableCell>
                            <TableCell align="right" sx={{ px: isMobile ? 0.5 : 1, fontSize: isMobile ? '0.75rem' : '0.875rem', whiteSpace: 'nowrap' }}>
                                {row.batAvg?.toFixed(1) || '0'} @ {row.batSR?.toFixed(0) || '0'}
                            </TableCell>
                            <TableCell align="right" sx={{ px: isMobile ? 0.5 : 1, fontSize: isMobile ? '0.75rem' : '0.875rem' }}>
                                {row.batBPD?.toFixed(1) || '0'}
                            </TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </TableContainer>
    );
};

const BowlingLeaders = ({ data, isMobile }) => {
    if (!data || data.length === 0) return null;

    return (
        <TableContainer sx={{ overflowX: 'hidden' }}>
            <Typography variant="h6" gutterBottom align="center">Most Wickets</Typography>
            <Table size="small">
                <TableHead>
                    <TableRow>
                        <TableCell sx={{ px: isMobile ? 0.5 : 1 }}>Name</TableCell>
                        <TableCell align="right" sx={{ px: isMobile ? 0.5 : 1 }}>Inns</TableCell>
                        <TableCell align="right" sx={{ px: isMobile ? 0.5 : 1 }}>Wkts</TableCell>
                        <TableCell align="right" sx={{ px: isMobile ? 0.5 : 1 }}>Avg @ ER</TableCell>
                        <TableCell align="right" sx={{ px: isMobile ? 0.5 : 1 }}>BPD</TableCell>
                    </TableRow>
                </TableHead>
                <TableBody>
                    {data.map((row, index) => (
                        <TableRow
                            key={`${row.name}-${index}`}
                            sx={{ '&:nth-of-type(odd)': { backgroundColor: 'rgba(0, 0, 0, 0.04)' } }}
                        >
                            <TableCell sx={{ px: isMobile ? 0.5 : 1, fontSize: isMobile ? '0.75rem' : '0.875rem' }}>
                                <Box
                                    component="span"
                                    sx={{
                                        cursor: 'help',
                                        textDecoration: 'underline',
                                        textDecorationStyle: 'dotted'
                                    }}
                                    title={`Teams: ${row.bowling_team}`}
                                >
                                    {row.name}
                                </Box>
                            </TableCell>
                            <TableCell align="right" sx={{ px: isMobile ? 0.5 : 1, fontSize: isMobile ? '0.75rem' : '0.875rem' }}>
                                {row.bowlInns}
                            </TableCell>
                            <TableCell align="right" sx={{ px: isMobile ? 0.5 : 1, fontSize: isMobile ? '0.75rem' : '0.875rem' }}>
                                {row.bowlWickets}
                            </TableCell>
                            <TableCell align="right" sx={{ px: isMobile ? 0.5 : 1, fontSize: isMobile ? '0.75rem' : '0.875rem', whiteSpace: 'nowrap' }}>
                                {row.bowlAvg?.toFixed(1) || '0'} @ {row.bowlER?.toFixed(1) || '0'}
                            </TableCell>
                            <TableCell align="right" sx={{ px: isMobile ? 0.5 : 1, fontSize: isMobile ? '0.75rem' : '0.875rem' }}>
                                {row.bowlBPD?.toFixed(1) || '0'}
                            </TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </TableContainer>
    );
};

const VenueNotes = ({ 
    venue, 
    startDate, 
    endDate, 
    venueStats, 
    statsData, 
    selectedTeam1, 
    selectedTeam2, 
    venueFantasyStats, 
    venuePlayerHistory,
    matchHistory,
    isMobile 
  }) => {

    const [fantasyTabValue, setFantasyTabValue] = useState(0);

const WinPercentagesPie = ({ data }) => {
    const theme = useTheme();
    const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

    // Responsive height calculation - fits in mobile viewport for screenshots
    const chartHeight = isMobile ?
        Math.min(typeof window !== 'undefined' ? window.innerHeight * 0.45 : 300, 320) :
        350;

    const totalDecisiveMatches = data.batting_first_wins + data.batting_second_wins;
    const battingFirstPct = totalDecisiveMatches > 0 ?
        (data.batting_first_wins / totalDecisiveMatches) * 100 : 0;
    const fieldingFirstPct = totalDecisiveMatches > 0 ?
        (data.batting_second_wins / totalDecisiveMatches) * 100 : 0;

    const pieData = [
        {
            name: 'Won Batting First',
            value: battingFirstPct,
            count: data.batting_first_wins
        },
        {
            name: 'Won Fielding First',
            value: fieldingFirstPct,
            count: data.batting_second_wins
        }
    ];

    const COLORS = ['#003f5c', '#bc5090'];

    const renderCustomizedLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent, index }) => {
      const RADIAN = Math.PI / 180;
      const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
      const x = cx + radius * Math.cos(-midAngle * RADIAN);
      const y = cy + radius * Math.sin(-midAngle * RADIAN);

      return (
        <text
          x={x}
          y={y}
          fill="white"
          textAnchor="middle"
          dominantBaseline="central"
          fontSize={isMobile ? 14 : 16}
          fontWeight="bold"
        >
          {`${(percent * 100).toFixed(1)}%`}
        </text>
      );
    };

    // Calculate explicit height for the chart container (chartHeight minus title ~35px and legend ~50px)
    const chartContainerHeight = chartHeight - 85;

    return (
        <Box sx={{ width: '100%', height: chartHeight, display: 'flex', flexDirection: 'column' }}>
            <Typography variant={isMobile ? "body1" : "subtitle1"} align="center" gutterBottom sx={{ fontWeight: 600 }}>
                Match Results Distribution
            </Typography>
            <Box sx={{ width: '100%', height: chartContainerHeight }}>
                <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                        <Pie
                            data={pieData}
                            cx="50%"
                            cy={isMobile ? "45%" : "40%"}
                            innerRadius={isMobile ? 45 : 60}
                            outerRadius={isMobile ? 90 : 110}
                            paddingAngle={3}
                            dataKey="value"
                            nameKey="name"
                            labelLine={false}
                            label={renderCustomizedLabel}
                        >
                            {pieData.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                            ))}
                        </Pie>
                        <Tooltip
                            formatter={(value, name, props) => [`${props.payload.count} wins (${value.toFixed(1)}%)`, name]}
                        />
                    </PieChart>
                </ResponsiveContainer>
            </Box>
            {/* Legend moved below chart for better mobile layout */}
            <Box sx={{
                display: 'flex',
                justifyContent: 'center',
                gap: isMobile ? 2 : 3,
                flexWrap: 'wrap',
                mt: isMobile ? 0 : 1,
                pb: 1
            }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <Box sx={{ width: 12, height: 12, bgcolor: COLORS[0], borderRadius: '50%' }} />
                    <Typography variant="caption" sx={{ fontSize: isMobile ? '0.7rem' : '0.75rem' }}>
                        Won Batting First ({data.batting_first_wins})
                    </Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <Box sx={{ width: 12, height: 12, bgcolor: COLORS[1], borderRadius: '50%' }} />
                    <Typography variant="caption" sx={{ fontSize: isMobile ? '0.7rem' : '0.75rem' }}>
                        Won Fielding First ({data.batting_second_wins})
                    </Typography>
                </Box>
            </Box>
        </Box>
    );
};

const ScoresBarChart = ({ data }) => {
    const theme = useTheme();
    const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

    // Responsive height calculation - fits in mobile viewport for screenshots
    const chartHeight = isMobile ?
        Math.min(typeof window !== 'undefined' ? window.innerHeight * 0.5 : 320, 350) :
        350;

    const scoreData = [
        {
            name: '1st Innings Avg',
            shortName: '1st Inn',
            value: Math.round(data.average_first_innings || 0),
        },
        {
            name: '2nd Innings Avg',
            shortName: '2nd Inn',
            value: Math.round(data.average_second_innings || 0),
        },
        {
            name: 'Avg Winning Score',
            shortName: 'Win Score',
            value: Math.round(data.average_winning_score || 0),
        },
        {
            name: 'Avg Chasing Score',
            shortName: 'Chase Score',
            value: Math.round(data.average_chasing_score || 0),
        },
        {
            name: 'Highest Total',
            shortName: 'Highest',
            value: data.highest_total || 0,
        },
        {
            name: 'Highest Chased',
            shortName: 'High Chase',
            value: data.highest_total_chased || 0,
        },
        {
            name: 'Lowest Defended',
            shortName: 'Low Defend',
            value: data.lowest_total_defended || 0,
        },
        {
            name: 'Lowest Total',
            shortName: 'Lowest',
            value: data.lowest_total || 0,
        }
    ];

    // Filter out zero values which might be causing display issues
    const filteredScoreData = scoreData.filter(item => item.value > 0);

    // Custom bar label component to ensure values are displayed
    const CustomBarLabel = (props) => {
        const { x, y, width, value, height } = props;
        return (
            <text
                x={x + width + 5}
                y={y + height / 2}
                fill="#666"
                fontSize={isMobile ? 10 : 12}
                textAnchor="start"
                dominantBaseline="middle"
            >
                {value}
            </text>
        );
    };

    // Calculate explicit height for the chart container (chartHeight minus title ~35px)
    const chartContainerHeight = chartHeight - 35;

    return (
        <Box sx={{ width: '100%', height: chartHeight, display: 'flex', flexDirection: 'column' }}>
            <Typography variant={isMobile ? "body1" : "subtitle1"} align="center" gutterBottom sx={{ fontWeight: 600 }}>
                Innings Scores Analysis
            </Typography>
            <Box sx={{ width: '100%', height: chartContainerHeight }}>
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                        data={filteredScoreData}
                        layout="vertical"
                        margin={{
                            top: 10,
                            right: isMobile ? 35 : 50,
                            left: isMobile ? 5 : 10,
                            bottom: isMobile ? 10 : 20
                        }}
                    >
                        <XAxis
                            type="number"
                            domain={[0, 'dataMax + 20']}
                            axisLine={true}
                            grid={false}
                            tick={{ fontSize: isMobile ? 9 : 12 }}
                            label={isMobile ? undefined : { value: 'Runs', position: 'bottom', offset: 0 }}
                        />
                        <YAxis
                            type="category"
                            dataKey={isMobile ? "shortName" : "name"}
                            width={isMobile ? 65 : 120}
                            axisLine={false}
                            tickLine={false}
                            tick={{ fontSize: isMobile ? 9 : 12 }}
                        />
                        <Tooltip
                            formatter={(value, name, props) => [value, props.payload.name]}
                        />
                        <Bar
                            dataKey="value"
                            fill="#E6E6FA"
                            label={<CustomBarLabel />}
                            isAnimationActive={false}
                        />
                    </BarChart>
                </ResponsiveContainer>
            </Box>
        </Box>
    );
};

const PhaseWiseStrategy = ({ data, isMobile }) => {
    const PHASE_OVERS = [
        { start: 0, end: 6, label: 'powerplay' },
        { start: 6, end: 10, label: 'middle1' },
        { start: 10, end: 15, label: 'middle2' },
        { start: 15, end: 20, label: 'death' }
    ];
    
    const processPhaseData = (phaseStats) => {
        if (!phaseStats) return [];
        
        return PHASE_OVERS.map(phase => ({
            ...phase,
            width: ((phase.end - phase.start) / 20) * 100,
            stats: phaseStats[phase.label] || {
                runs_per_innings: 0,
                wickets_per_innings: 0,
                balls_per_innings: 0
            }
        }));
    };

    const renderPhase = (phaseData, title) => (
        <Box>
            <Typography variant={isMobile ? "body1" : "subtitle2"} sx={{ mb: 1 }}>{title}</Typography>
            <Box sx={{ 
                display: 'flex',
                flexDirection: 'column',
                width: '100%'
            }}>
                <Box sx={{ 
                    display: 'flex',
                    width: '100%',
                    height: isMobile ? 40 : 50,
                    backgroundColor: '#f5f5f5',
                    borderRadius: '4px 4px 0 0',
                    overflow: 'hidden'
                }}>
                    {phaseData.map((phase, index) => (
                        <Box
                            key={phase.label}
                            sx={{
                                width: `${phase.width}%`,
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                backgroundColor: index % 2 === 0 ? '#5a8691' : '#55ae6a',
                                color: 'white',
                                fontSize: isMobile ? '0.7rem' : '0.875rem',
                                borderRight: index < phaseData.length - 1 ? '1px solid rgba(255,255,255,0.2)' : 'none'
                            }}
                        >
                            {`${Math.round(phase.stats.runs_per_innings)}-${Math.round(phase.stats.wickets_per_innings)}${!isMobile ? ` (${Math.round(phase.stats.balls_per_innings)})` : ''}`}
                        </Box>
                    ))}
                </Box>
                <Box sx={{ 
                    display: 'flex',
                    width: '100%',
                    height: isMobile ? 16 : 20,
                    borderTop: '1px solid #ddd'
                }}>
                    {phaseData.map((phase, index) => (
                        <Box
                            key={`over-${phase.label}`}
                            sx={{
                                width: `${phase.width}%`,
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                fontSize: isMobile ? '0.65rem' : '0.75rem',
                                color: '#666',
                                borderRight: index < phaseData.length - 1 ? '1px solid #ddd' : 'none'
                            }}
                        >
                            {`${phase.start}-${phase.end}`}
                        </Box>
                    ))}
                </Box>
            </Box>
        </Box>
    );

    const firstInningsData = processPhaseData(data.phase_wise_stats?.batting_first_wins);
    const secondInningsData = processPhaseData(data.phase_wise_stats?.chasing_wins);

    return (
        <Box sx={{ mt: 2 }}>
            <Typography variant={isMobile ? "h6" : "h5"} gutterBottom>Phase-wise Strategy</Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                {renderPhase(firstInningsData, "Batting First")}
                {renderPhase(secondInningsData, "Chasing")}
            </Box>
        </Box>
    );
};

if (!venueStats) return <Alert severity="info">Please select a venue</Alert>;

return (
    <Box sx={{ p: { xs: 1, sm: 2 } }}>
        <Typography variant={isMobile ? "h5" : "h4"} gutterBottom>
            {venue === "All Venues" ? 
                `All Venues - ${venueStats.total_matches} T20s` : 
                `${venue} - ${venueStats.total_matches} T20s`
            }
            <Typography variant="subtitle1" color="text.secondary">
                {startDate} to {endDate}
            </Typography>
        </Typography>
        <Grid container spacing={isMobile ? 2 : 3}>
            <Grid item xs={12} md={6}>
                <Card sx={{ p: { xs: 0, sm: 2 }, width: '100%', boxShadow: isMobile ? 0 : undefined, backgroundColor: isMobile ? 'transparent' : undefined }}>
                    <WinPercentagesPie data={venueStats} />
                </Card>
            </Grid>
            <Grid item xs={12} md={6}>
                <Card sx={{ p: { xs: 0, sm: 2 }, width: '100%', boxShadow: isMobile ? 0 : undefined, backgroundColor: isMobile ? 'transparent' : undefined }}>
                    <ScoresBarChart data={venueStats} />
                </Card>
            </Grid>
            <Grid item xs={12} md={12}>
                <Card sx={{ p: { xs: 0, sm: 2 }, width: '100%', boxShadow: isMobile ? 0 : undefined, backgroundColor: isMobile ? 'transparent' : undefined }}>
                    <PhaseWiseStrategy data={venueStats} isMobile={isMobile} />
                </Card>
            </Grid>
            
            {/* Contextual Query Prompts */}
            <Grid item xs={12}>
                <ContextualQueryPrompts 
                    queries={getVenueContextualQueries(venue, {
                        startDate,
                        endDate,
                        leagues: [],
                        team1: selectedTeam1,
                        team2: selectedTeam2,
                    })}
                    title={`🔍 Explore ${venue.split(',')[0]} Data`}
                />
            </Grid>
            
            {selectedTeam1 && selectedTeam2 && matchHistory && (
                <>
                    <Grid item xs={12}>
                        <Typography variant="h5" gutterBottom sx={{ mt: 2, mb: 1 }}>
                            Team Performance Analysis
                        </Typography>
                    </Grid>
                    
                    <Grid item xs={12}>
                        <MatchHistory 
                            venue={venue}
                            team1={selectedTeam1.abbreviated_name}
                            team2={selectedTeam2.abbreviated_name}
                            venueResults={matchHistory.venue_results}
                            team1Results={matchHistory.team1_results}
                            team2Results={matchHistory.team2_results}
                            h2hStats={matchHistory.h2h_stats}
                            isMobile={isMobile}
                        />
                    </Grid>
                </>
            )}
            
            {selectedTeam1 && selectedTeam2 && (
                <>
                    <Grid item xs={12}>
                        <Divider sx={{ my: 3 }} />
                        <Typography variant="h5" gutterBottom>
                            Player Matchups
                        </Typography>
                        <Matchups
                            team1={selectedTeam1.full_name}
                            team2={selectedTeam2.full_name}
                            startDate={startDate}
                            endDate={endDate}
                            isMobile={isMobile}
                        />
                    </Grid>

                    <Grid item xs={12} md={12}>
                        <Card sx={{ p: 2, width: '100%', mt: 3 }}>
                            <Typography variant="h6" gutterBottom>
                                Fantasy Points Analysis
                            </Typography>
                            <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
                                <Tabs value={fantasyTabValue} onChange={(e, newValue) => setFantasyTabValue(newValue)}>
                                    <Tab label="Team Comparison" />
                                    <Tab label="Venue History" />
                                </Tabs>
                            </Box>
                            <Box sx={{ mt: 2 }}>
                                {fantasyTabValue === 0 && (
                                    <>
                                        <Grid container spacing={isMobile ? 1 : 2}>
                                            <Grid item xs={12} md={6}>
                                                <FantasyPointsTable 
                                                    players={venueFantasyStats?.team1_players || []} 
                                                    title={`${selectedTeam1.abbreviated_name} Fantasy Points at ${venue}`} 
                                                    isMobile={isMobile}
                                                />
                                            </Grid>
                                            <Grid item xs={12} md={6}>
                                                <FantasyPointsTable 
                                                    players={venueFantasyStats?.team2_players || []} 
                                                    title={`${selectedTeam2.abbreviated_name} Fantasy Points at ${venue}`} 
                                                    isMobile={isMobile}
                                                />
                                            </Grid>
                                        </Grid>         
                                        <Grid container spacing={isMobile ? 1 : 2} sx={{ mt: 2 }}>
                                            <Grid item xs={12} md={6}>
                                                <FantasyPointsBarChart 
                                                    players={venueFantasyStats?.team1_players || []} 
                                                    title={`${selectedTeam1.abbreviated_name} Fantasy Points Breakdown`} 
                                                    isMobile={isMobile}
                                                />
                                            </Grid>
                                            <Grid item xs={12} md={6}>
                                                <FantasyPointsBarChart 
                                                    players={venueFantasyStats?.team2_players || []} 
                                                    title={`${selectedTeam2.abbreviated_name} Fantasy Points Breakdown`} 
                                                    isMobile={isMobile}
                                                />
                                            </Grid>
                                        </Grid> 
                                    </>
                                )}
                                {fantasyTabValue === 1 && (
                                    <>
                                        <FantasyPointsTable 
                                            players={venuePlayerHistory?.players || []} 
                                            title={`Player Fantasy History at ${venue}`} 
                                            isMobile={isMobile}
                                        />
                                        <FantasyPointsBarChart 
                                            players={venuePlayerHistory?.players || []} 
                                            title={`Top Players at ${venue}`} 
                                            isMobile={isMobile}
                                        />
                                    </>
                                )}
                            </Box>
                        </Card>
                    </Grid>
                </>
            )}
            
            {statsData?.batting_leaders && statsData.batting_leaders.length > 0 && (
                <Grid item xs={12} md={6}>
                    <Card sx={{ p: { xs: 0, sm: 2 }, width: '100%', boxShadow: isMobile ? 0 : undefined, backgroundColor: isMobile ? 'transparent' : undefined }}>
                        <BattingLeaders data={statsData.batting_leaders} isMobile={isMobile} />
                    </Card>
                </Grid>
            )}
            {statsData?.bowling_leaders && statsData.bowling_leaders.length > 0 && (
                <Grid item xs={12} md={6}>
                    <Card sx={{ p: { xs: 0, sm: 2 }, width: '100%', boxShadow: isMobile ? 0 : undefined, backgroundColor: isMobile ? 'transparent' : undefined }}>
                        <BowlingLeaders data={statsData.bowling_leaders} isMobile={isMobile} />
                    </Card>
                </Grid>
            )}
            
            {statsData?.batting_scatter && statsData.batting_scatter.length > 0 && (
                <Grid item xs={12} md={12}>
                    <BattingScatterChart data={statsData.batting_scatter} isMobile={isMobile} />
                </Grid>
            )}
            {statsData?.batting_scatter && statsData.batting_scatter.length > 0 && (
                <Grid item xs={12} md={12}>
                    <Card sx={{
                        p: { xs: 1, sm: 2 },
                        width: '100%',
                        backgroundColor: isMobile ? 'transparent' : undefined,
                        boxShadow: isMobile ? 0 : undefined
                    }}>
                        <Typography variant={isMobile ? "body1" : "h6"} gutterBottom sx={{ fontWeight: 600 }}>
                            Bowling Type Analysis
                        </Typography>
                        {/* Wrap BowlingAnalysis in error boundary */}
                        <Box sx={{ position: 'relative' }}>
                            <BowlingAnalysis
                            venue={venue}
                            startDate={startDate}
                            endDate={endDate}
                                isMobile={isMobile}
                        />
                        </Box>
                    </Card>
                </Grid>
            )}
        </Grid>
        
        {/* Credits Section */}
        <Box sx={{ mt: 6, mb: 3, pt: 4, borderTop: '1px solid #eee' }}>
            <Typography variant="h6" gutterBottom align="center">
                Credits & Acknowledgements
            </Typography>
            <Grid container spacing={3} sx={{ mt: 1 }}>
                <Grid item xs={12} md={4}>
                    <Typography variant="subtitle2" gutterBottom color="primary">
                        Data Sources
                    </Typography>
                    <Typography variant="body2" paragraph>
                        Ball-by-ball data from <a href="https://cricsheet.org/" target="_blank" rel="noopener noreferrer">Cricsheet.org</a>
                    </Typography>
                    <Typography variant="body2" paragraph>
                        Player information from <a href="https://cricmetric.com/" target="_blank" rel="noopener noreferrer">Cricmetric</a>
                    </Typography>
                </Grid>
                
                <Grid item xs={12} md={4}>
                    <Typography variant="subtitle2" gutterBottom color="primary">
                        Metrics & Visualization Inspiration
                    </Typography>
                    <Typography variant="body2" component="div">
                        <Box component="span" sx={{ display: 'inline-block', mr: 1, mb: 0.5 }}>
                            <a href="https://twitter.com/prasannalara" target="_blank" rel="noopener noreferrer">@prasannalara</a>
                        </Box>
                        <Box component="span" sx={{ display: 'inline-block', mr: 1, mb: 0.5 }}>
                            <a href="https://twitter.com/cricketingview" target="_blank" rel="noopener noreferrer">@cricketingview</a>
                        </Box>
                        <Box component="span" sx={{ display: 'inline-block', mr: 1, mb: 0.5 }}>
                            <a href="https://twitter.com/IndianMourinho" target="_blank" rel="noopener noreferrer">@IndianMourinho</a>
                        </Box>
                        <Box component="span" sx={{ display: 'inline-block', mr: 1, mb: 0.5 }}>
                            <a href="https://twitter.com/hganjoo_153" target="_blank" rel="noopener noreferrer">@hganjoo_153</a>
                        </Box>
                        <Box component="span" sx={{ display: 'inline-block', mr: 1, mb: 0.5 }}>
                            <a href="https://twitter.com/randomcricstat" target="_blank" rel="noopener noreferrer">@randomcricstat</a>
                        </Box>
                        <Box component="span" sx={{ display: 'inline-block', mr: 1, mb: 0.5 }}>
                            <a href="https://twitter.com/kaustats" target="_blank" rel="noopener noreferrer">@kaustats</a>
                        </Box>
                        <Box component="span" sx={{ display: 'inline-block', mr: 1, mb: 0.5 }}>
                            <a href="https://twitter.com/cricviz" target="_blank" rel="noopener noreferrer">@cricviz</a>
                        </Box>
                        <Box component="span" sx={{ display: 'inline-block', mr: 1, mb: 0.5 }}>
                            <a href="https://twitter.com/ajarrodkimber" target="_blank" rel="noopener noreferrer">@ajarrodkimber</a>
                        </Box>
                    </Typography>
                </Grid>
                
                <Grid item xs={12} md={4}>
                    <Typography variant="subtitle2" gutterBottom color="primary">
                        Development Assistance
                    </Typography>
                    <Typography variant="body2" paragraph>
                        Claude and ChatGPT for Vibe Coding my way through this project
                    </Typography>
                </Grid>
            </Grid>
            
            <Typography variant="body2" color="textSecondary" align="center" sx={{ mt: 3, pb: 2 }}>
                Cricket Data Thing © {new Date().getFullYear()} - Advanced cricket analytics and visualization
            </Typography>
        </Box>
    </Box>
);
};

export default VenueNotes;