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

const BattingScatter = ({ data, isMobile }) => {
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
    
    if (!data || data.length === 0) return null;

    const avgBatter = data.find(d => d.name === 'Average Batter');
    if (!avgBatter) return null;

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
    const axisData = filteredData.map(d => ({
        x: d[metrics.xKey],
        y: d[metrics.yKey]
    }));

    const padding = 0.05;
    const minX = Math.floor(Math.min(...axisData.map(d => d.x)) * (1 - padding));
    const maxX = Math.ceil(Math.max(...axisData.map(d => d.x)) * (1 + padding));
    const minY = Math.floor(Math.min(...axisData.map(d => d.y)) * (1 - padding));
    const maxY = Math.ceil(Math.max(...axisData.map(d => d.y)) * (1 + padding));

    return (
        <Box sx={{ width: '100%', height: isMobile ? 450 : 550, pt: 2 }}>
            <Typography variant="h6" sx={{ px: 2, mb: 2 }}>
                Batting Performance Analysis
            </Typography>
            
            <Stack 
                direction={isMobile ? "column" : "row"} 
                spacing={2} 
                alignItems={isMobile ? "stretch" : "center"} 
                sx={{ px: 2, mb: 2 }}
            >
                <Box sx={{ width: isMobile ? "100%" : 200 }}>
                    <Typography variant="body2" gutterBottom>
                        Minimum Innings: {minInnings}
                    </Typography>
                    <Slider
                        value={minInnings}
                        onChange={(_, value) => setMinInnings(value)}
                        min={1}
                        max={20}
                        step={1}
                    />
                </Box>
                <FormControl sx={{ width: isMobile ? "100%" : 150 }}>
                    <InputLabel>Phase</InputLabel>
                    <Select
                        value={phase}
                        onChange={(e) => setPhase(e.target.value)}
                        label="Phase"
                    >
                        {phases.map(p => (
                            <MenuItem key={p.value} value={p.value}>{p.label}</MenuItem>
                        ))}
                    </Select>
                </FormControl>
                <FormControl sx={{ width: isMobile ? "100%" : 200 }}>
                    <InputLabel>Plot Type</InputLabel>
                    <Select
                        value={plotType}
                        onChange={(e) => setPlotType(e.target.value)}
                        label="Plot Type"
                    >
                        {plotTypes.map(p => (
                            <MenuItem key={p.value} value={p.value}>{p.label}</MenuItem>
                        ))}
                    </Select>
                </FormControl>
            </Stack>

            <Box sx={{ height: isMobile ? 400 : 500, width: '100%' }}>
                <ResponsiveContainer>
                    <ScatterChart 
                        margin={{ 
                            top: 20, 
                            right: isMobile ? 20 : 30, 
                            bottom: isMobile ? 30 : 50, 
                            left: isMobile ? 40 : 60 
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
                            name={metrics.xLabel}
                            label={isMobile ? null : { value: metrics.xLabel, position: 'bottom' }}
                            domain={[minX, maxX]}
                            tick={{ fontSize: isMobile ? 10 : 12 }}
                        />
                        <YAxis 
                            type="number" 
                            dataKey={metrics.yKey}
                            name={metrics.yLabel}
                            label={isMobile ? null : { value: metrics.yLabel, angle: -90, position: 'left' }}
                            domain={[minY, maxY]}
                            tick={{ fontSize: isMobile ? 10 : 12 }}
                        />
                        
                        <ReferenceLine x={avgBatter[metrics.xKey]} stroke="#666" strokeDasharray="3 3" />
                        <ReferenceLine y={avgBatter[metrics.yKey]} stroke="#666" strokeDasharray="3 3" />

                        <Tooltip content={<CustomTooltip />} />
                        <Legend />

                        <Scatter
                            name="Players"
                            data={filteredData.slice(0, 12)} // Limit to top 12 players to prevent overcrowding
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
                                            y={cy + 16}
                                            textAnchor="middle"
                                            fontSize={11}
                                            fontWeight="normal"
                                            fill="#333"
                                        >
                                            {payload.name.length > 10 ? payload.name.substring(0, 10) + '...' : payload.name}
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
                                        {/* Diamond shape for Average Batter */}
                                        <polygon
                                            points={`${cx},${cy-8} ${cx+8},${cy} ${cx},${cy+8} ${cx-8},${cy}`}
                                            fill="#000"
                                            stroke="#fff"
                                            strokeWidth={1}
                                        />
                                        <text
                                            x={cx}
                                            y={cy + 16}
                                            textAnchor="middle"
                                            fontSize={11}
                                            fontWeight="bold"
                                            fill="#333"
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

const BattingLeaders = ({ data }) => {
    if (!data || data.length === 0) return null;
    
    return (
        <TableContainer>
            <Typography variant="h6" gutterBottom align="center">Most Runs</Typography>
            <Table size="small">
                <TableHead>
                    <TableRow>
                        <TableCell>Name</TableCell>
                        <TableCell align="right">Inns</TableCell>
                        <TableCell align="right">Runs</TableCell>
                        <TableCell align="right">Avg</TableCell>
                        <TableCell align="right">SR</TableCell>
                        <TableCell align="right">BPD</TableCell>
                    </TableRow>
                </TableHead>
                <TableBody>
                    {data.map((row, index) => (
                        <TableRow 
                            key={`${row.name}-${index}`} 
                            sx={{ '&:nth-of-type(odd)': { backgroundColor: 'rgba(0, 0, 0, 0.04)' } }}
                        >
                            <TableCell>
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
                            <TableCell align="right">{row.batInns}</TableCell>
                            <TableCell align="right">{row.batRuns}</TableCell>
                            <TableCell align="right">{row.batAvg?.toFixed(2) || '0.00'}</TableCell>
                            <TableCell align="right">{row.batSR?.toFixed(2) || '0.00'}</TableCell>
                            <TableCell align="right">{row.batBPD?.toFixed(2) || '0.00'}</TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </TableContainer>
    );
};

const BowlingLeaders = ({ data }) => {
    if (!data || data.length === 0) return null;

    return (
        <TableContainer>
            <Typography variant="h6" gutterBottom align="center">Most Wickets</Typography>
            <Table size="small">
                <TableHead>
                    <TableRow>
                        <TableCell>Name</TableCell>
                        <TableCell align="right">Inns</TableCell>
                        <TableCell align="right">Wkts</TableCell>
                        <TableCell align="right">Avg</TableCell>
                        <TableCell align="right">SR</TableCell>
                        <TableCell align="right">ER</TableCell>
                    </TableRow>
                </TableHead>
                <TableBody>
                    {data.map((row, index) => (
                        <TableRow 
                        key={`${row.name}-${index}`} 
                        sx={{ '&:nth-of-type(odd)': { backgroundColor: 'rgba(0, 0, 0, 0.04)' } }}
                    >
                        <TableCell>
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
                        <TableCell align="right">{row.bowlInns}</TableCell>
                        <TableCell align="right">{row.bowlWickets}</TableCell>
                        <TableCell align="right">{row.bowlAvg?.toFixed(2) || '0.00'}</TableCell>
                        <TableCell align="right">{row.bowlBPD?.toFixed(2) || '0.00'}</TableCell>
                        <TableCell align="right">{row.bowlER?.toFixed(2) || '0.00'}</TableCell>
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

    const renderCustomizedLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent, index, name, count }) => {
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
          fontSize={isMobile ? 12 : 14}
        >
          {`${pieData[index].count} (${(percent * 100).toFixed(1)}%)`}
        </text>
      );
    };

    return (
        <Box sx={{ width: '100%', height: isMobile ? 250 : 350 }}>
            <Typography variant="subtitle1" align="center" gutterBottom>
                Match Results Distribution
            </Typography>
            <ResponsiveContainer>
                <PieChart>
                    <Pie
                        data={pieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={isMobile ? 40 : 60}
                        outerRadius={isMobile ? 80 : 110}
                        paddingAngle={2}
                        dataKey="value"
                        nameKey="name"
                        labelLine={false}
                        label={renderCustomizedLabel}
                    >
                        {pieData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                    </Pie>
                    <Legend />
                    <Tooltip 
                        formatter={(value, name, props) => [`${props.payload.count} (${value.toFixed(1)}%)`, name]}
                    />
                </PieChart>
            </ResponsiveContainer>
        </Box>
    );
};

const ScoresBarChart = ({ data }) => {
    const theme = useTheme();
    const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
    const scoreData = [
        {
            name: '1st Innings Avg',
            value: Math.round(data.average_first_innings || 0),
        },
        {
            name: '2nd Innings Avg',
            value: Math.round(data.average_second_innings || 0),
        },
        {
            name: 'Avg Winning Score',
            value: Math.round(data.average_winning_score || 0),
        },
        {
            name: 'Avg Chasing Score',
            value: Math.round(data.average_chasing_score || 0),
        },
        {
            name: 'Highest Total',
            value: data.highest_total || 0,
        },
        {
            name: 'Highest Chased',
            value: data.highest_total_chased || 0,
        },
        {
            name: 'Lowest Defended',
            value: data.lowest_total_defended || 0,
        },
        {
            name: 'Lowest Total',
            value: data.lowest_total || 0,
        }
    ];

    // Filter out zero values which might be causing display issues
    const filteredScoreData = scoreData.filter(item => item.value > 0);
    
    const formatTooltip = (value, name) => [value, name];

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

    return (
        <Box sx={{ width: '100%', height: isMobile ? 250 : 350 }}>
            <Typography variant="subtitle1" align="center" gutterBottom>
                Innings Scores Analysis
            </Typography>
            <ResponsiveContainer width="100%" height="100%">
                <BarChart
                    data={filteredScoreData}
                    layout="vertical"
                    margin={{ 
                        top: 20, 
                        right: isMobile ? 50 : 70, // Increased right margin to accommodate labels
                        left: isMobile ? 10 : 20, 
                        bottom: 20 
                    }}
                >
                    <XAxis 
                        type="number" 
                        domain={[0, 'dataMax + 20']}
                        axisLine={true}
                        grid={false}
                        tick={{ fontSize: isMobile ? 10 : 12 }}
                    />
                    <YAxis 
                        type="category" 
                        dataKey="name" 
                        width={isMobile ? 90 : 120}
                        axisLine={false}
                        tickLine={false}
                        tick={{ fontSize: isMobile ? 9 : 12 }}
                    />
                    <Tooltip formatter={formatTooltip} />
                    <Bar 
                        dataKey="value" 
                        fill="#E6E6FA"  // Pastel purple
                        label={<CustomBarLabel />}
                        isAnimationActive={false}  // Disable animation to ensure labels render immediately
                    />
                </BarChart>
            </ResponsiveContainer>
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
                <Card sx={{ p: { xs: 1, sm: 2 }, width: '100%' }}>
                    <WinPercentagesPie data={venueStats} />
                </Card>
            </Grid>
            <Grid item xs={12} md={6}>
                <Card sx={{ p: { xs: 1, sm: 2 }, width: '100%' }}>
                    <ScoresBarChart data={venueStats} />
                </Card>
            </Grid>
            <Grid item xs={12} md={12}>
                <Card sx={{ p: { xs: 1, sm: 2 }, width: '100%' }}>
                    <PhaseWiseStrategy data={venueStats} isMobile={isMobile} />
                </Card>
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
                    <Card sx={{ p: { xs: 1, sm: 2 }, width: '100%', overflowX: 'auto' }}>
                        <BattingLeaders data={statsData.batting_leaders} isMobile={isMobile} />
                    </Card>
                </Grid>
            )}
            {statsData?.bowling_leaders && statsData.bowling_leaders.length > 0 && (
                <Grid item xs={12} md={6}>
                    <Card sx={{ p: { xs: 1, sm: 2 }, width: '100%', overflowX: 'auto' }}>
                        <BowlingLeaders data={statsData.bowling_leaders} isMobile={isMobile} />
                    </Card>
                </Grid>
            )}
            
            {statsData?.batting_scatter && statsData.batting_scatter.length > 0 && (
                <Grid item xs={12} md={12}>
                    <Card sx={{ p: { xs: 1, sm: 2 }, width: '100%' }}>
                        <BattingScatter data={statsData.batting_scatter} isMobile={isMobile} />
                    </Card>
                </Grid>
            )}
            {statsData?.batting_scatter && statsData.batting_scatter.length > 0 && (
                <Grid item xs={12} md={12}>
                    <Card sx={{ p: { xs: 1, sm: 2 }, width: '100%' }}>
                        <Typography variant="h6" gutterBottom>
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
    </Box>
);
};

export default VenueNotes;