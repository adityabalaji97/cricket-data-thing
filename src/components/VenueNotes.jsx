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
    Tab
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
} from 'recharts';
import BowlingAnalysis from './BowlingAnalysis';
import FantasyPointsTable from './FantasyPointsTable';
import FantasyPointsBarChart from './FantasyPointsBarChart';

const BattingScatter = ({ data }) => {
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
        }));

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
        <Box sx={{ width: '100%', height: 600, pt: 2 }}>
            <Stack direction="row" spacing={2} alignItems="center" sx={{ px: 2, mb: 2 }}>
                <Typography variant="h6" sx={{ flexGrow: 1 }}>
                    Batting Performance Analysis
                </Typography>
                <Box sx={{ width: 200 }}>
                    <Typography variant="body2" gutterBottom>
                        Minimum Innings: {minInnings}
                    </Typography>
                    <Slider
                        value={minInnings}
                        onChange={(_, value) => setMinInnings(value)}
                        min={1}
                        max={50}
                        step={1}
                    />
                </Box>
                <FormControl sx={{ width: 150 }}>
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
                <FormControl sx={{ width: 200 }}>
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

            <ResponsiveContainer>
                <ScatterChart margin={{ top: 20, right: 30, bottom: 50, left: 60 }}>
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
                        label={{ value: metrics.xLabel, position: 'bottom' }}
                        domain={[minX, maxX]}
                    />
                    <YAxis 
                        type="number" 
                        dataKey={metrics.yKey}
                        name={metrics.yLabel}
                        label={{ value: metrics.yLabel, angle: -90, position: 'left' }}
                        domain={[minY, maxY]}
                    />
                    
                    <ReferenceLine x={avgBatter[metrics.xKey]} stroke="#666" strokeDasharray="3 3" />
                    <ReferenceLine y={avgBatter[metrics.yKey]} stroke="#666" strokeDasharray="3 3" />

                    <Tooltip content={<CustomTooltip />} />

                    <Scatter
                        data={[...filteredData, avgBatter]}
                        shape={(props) => {
                            const { cx, cy, fill, payload } = props;
                            return (
                                <>
                                    <circle
                                        cx={cx}
                                        cy={cy}
                                        r={6}
                                        fill={fill || '#000'}
                                    />
                                    <text
                                        x={cx}
                                        y={cy + 15}
                                        textAnchor="middle"
                                        fontSize={12}
                                        fill="#000"
                                    >
                                        {payload.name}
                                    </text>
                                </>
                            );
                        }}
                    />
                </ScatterChart>
            </ResponsiveContainer>
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
    venuePlayerHistory 
  }) => {

    const [fantasyTabValue, setFantasyTabValue] = useState(0);

const WinPercentagesPie = ({ data }) => {
    const totalDecisiveMatches = data.batting_first_wins + data.batting_second_wins;
    const battingFirstPct = totalDecisiveMatches > 0 ? 
        (data.batting_first_wins / totalDecisiveMatches) * 100 : 0;
    const fieldingFirstPct = totalDecisiveMatches > 0 ? 
        (data.batting_second_wins / totalDecisiveMatches) * 100 : 0;
    
    const pieData = [
        { 
            name: 'Won Batting First', 
            value: battingFirstPct,
            label: `Won Batting First (${battingFirstPct.toFixed(1)}%)`
        },
        { 
            name: 'Won Fielding First', 
            value: fieldingFirstPct,
            label: `Won Fielding First (${fieldingFirstPct.toFixed(1)}%)`
        }
    ];

    return (
        <Box sx={{ width: '100%', height: 350 }}>
            <Typography variant="subtitle1" align="center" gutterBottom>
                Match Results Distribution
            </Typography>
            <ResponsiveContainer>
                <PieChart>
                    <Pie
                        data={pieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={110}
                        paddingAngle={2}
                        dataKey="value"
                        label={({ label, x, y }) => (
                            <text 
                                x={x} 
                                y={y} 
                                fill="#000" 
                                textAnchor={x > 250 ? 'start' : 'end'}
                                dominantBaseline="middle"
                                style={{ fontSize: '12px' }}
                            >
                                {label}
                            </text>
                        )}
                    >
                        <Cell fill="#003f5c" />
                        <Cell fill="#bc5090" />
                    </Pie>
                    <Tooltip />
                </PieChart>
            </ResponsiveContainer>
        </Box>
    );
};

const ScoresBarChart = ({ data }) => {
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

    const formatTooltip = (value, name) => [value, name];

    return (
        <Box sx={{ width: '100%', height: 350 }}>
            <Typography variant="subtitle1" align="center" gutterBottom>
                Innings Scores Analysis
            </Typography>
            <ResponsiveContainer width="100%" height="100%">
                <BarChart
                    data={scoreData}
                    layout="vertical"
                    margin={{ top: 20, right: 50, left: 20, bottom: 20 }}
                >
                    <XAxis 
                        type="number" 
                        domain={[0, 'dataMax + 20']}
                        axisLine={true}
                        grid={false}
                    />
                    <YAxis 
                        type="category" 
                        dataKey="name" 
                        width={120}
                        axisLine={false}
                        tickLine={false}
                    />
                    <Tooltip formatter={formatTooltip} />
                    <Bar 
                        dataKey="value" 
                        fill="#E6E6FA"  // Pastel purple
                        label={{ 
                            position: 'right',
                            formatter: (value) => `${value}`,
                            fill: '#666'
                        }}
                    />
                </BarChart>
            </ResponsiveContainer>
        </Box>
    );
};

const PhaseWiseStrategy = ({ data }) => {
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
            <Typography variant="subtitle2" sx={{ mb: 1 }}>{title}</Typography>
            <Box sx={{ 
                display: 'flex',
                flexDirection: 'column',
                width: '100%'
            }}>
                <Box sx={{ 
                    display: 'flex',
                    width: '100%',
                    height: 50,
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
                                fontSize: '0.875rem',
                                borderRight: index < phaseData.length - 1 ? '1px solid rgba(255,255,255,0.2)' : 'none'
                            }}
                        >
                            {`${Math.round(phase.stats.runs_per_innings)}-${Math.round(phase.stats.wickets_per_innings)} (${Math.round(phase.stats.balls_per_innings)})`}
                        </Box>
                    ))}
                </Box>
                <Box sx={{ 
                    display: 'flex',
                    width: '100%',
                    height: 20,
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
                                fontSize: '0.75rem',
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
            <Typography variant="h6" gutterBottom>Phase-wise Strategy</Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                {renderPhase(firstInningsData, "Batting First")}
                {renderPhase(secondInningsData, "Chasing")}
            </Box>
        </Box>
    );
};

if (!venueStats) return <Alert severity="info">Please select a venue</Alert>;

return (
    <Box sx={{ p: 2 }}>
        <Typography variant="h4" gutterBottom>
            {venue === "All Venues" ? 
                `All Venues - ${venueStats.total_matches} T20s` : 
                `${venue} - ${venueStats.total_matches} T20s`
            }
            <Typography variant="subtitle1" color="text.secondary">
                {startDate} to {endDate}
            </Typography>
        </Typography>
        <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
                <Card sx={{ p: 2, width: '100%' }}>
                    <WinPercentagesPie data={venueStats} />
                </Card>
            </Grid>
            <Grid item xs={12} md={6}>
                <Card sx={{ p: 2, width: '100%' }}>
                    <ScoresBarChart data={venueStats} />
                </Card>
            </Grid>
            <Grid item xs={12} md={12}>
                <Card sx={{ p: 2, width: '100%' }}>
                    <PhaseWiseStrategy data={venueStats} />
                </Card>
            </Grid>
            {statsData?.batting_leaders && statsData.batting_leaders.length > 0 && (
                <Grid item xs={12} md={6}>
                    <Card sx={{ p: 2, width: '100%' }}>
                        <BattingLeaders data={statsData.batting_leaders} />
                    </Card>
                </Grid>
            )}
            {statsData?.bowling_leaders && statsData.bowling_leaders.length > 0 && (
                <Grid item xs={12} md={6}>
                    <Card sx={{ p: 2, width: '100%' }}>
                        <BowlingLeaders data={statsData.bowling_leaders} />
                    </Card>
                </Grid>
            )}
            {statsData?.batting_scatter && statsData.batting_scatter.length > 0 && (
                <Grid item xs={12} md={12}>
                    <Card sx={{ p: 2, width: '100%' }}>
                        <BattingScatter data={statsData.batting_scatter} />
                    </Card>
                </Grid>
            )}
            {statsData?.batting_scatter && statsData.batting_scatter.length > 0 && (
                <Grid item xs={12} md={12}>
                    <Card sx={{ p: 2, width: '100%' }}>
                        <Typography variant="h6" gutterBottom>
                            Bowling Type Analysis
                        </Typography>
                        {/* Wrap BowlingAnalysis in error boundary */}
                        <Box sx={{ position: 'relative' }}>
                            <BowlingAnalysis 
                                venue={venue}
                                startDate={startDate}
                                endDate={endDate}
                            />
                        </Box>
                    </Card>
                </Grid>
            )}
            {selectedTeam1 && selectedTeam2 && (
            <Grid item xs={12} md={12}>
                <Card sx={{ p: 2, width: '100%' }}>
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
                        <Grid container spacing={2}>
                        <Grid item xs={12} md={6}>
                            <FantasyPointsTable 
                            players={venueFantasyStats?.team1_players || []} 
                            title={`${selectedTeam1.abbreviated_name} Fantasy Points at ${venue}`} 
                            />
                        </Grid>
                        <Grid item xs={12} md={6}>
                            <FantasyPointsTable 
                            players={venueFantasyStats?.team2_players || []} 
                            title={`${selectedTeam2.abbreviated_name} Fantasy Points at ${venue}`} 
                            />
                        </Grid>
                        </Grid>         
                        <Grid container spacing={2} sx={{ mt: 2 }}>
                        <Grid item xs={12} md={6}>
                            <FantasyPointsBarChart 
                            players={venueFantasyStats?.team1_players || []} 
                            title={`${selectedTeam1.abbreviated_name} Fantasy Points Breakdown`} 
                            />
                        </Grid>
                        <Grid item xs={12} md={6}>
                            <FantasyPointsBarChart 
                            players={venueFantasyStats?.team2_players || []} 
                            title={`${selectedTeam2.abbreviated_name} Fantasy Points Breakdown`} 
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
                        />
                        <FantasyPointsBarChart 
                        players={venuePlayerHistory?.players || []} 
                        title={`Top Players at ${venue}`} 
                        />
                     </>
                     )}
                    </Box>
                </Card>
            </Grid>
            )}
        </Grid>
    </Box>
);
};

export default VenueNotes;