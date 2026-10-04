import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import ShareButton from './ui/ShareButton';
import { useFormat } from '../context/FormatContext';
import { colors as hsColors } from '../theme/hindsightDark';
import {
  Box,
  Card,
  Grid,
  Typography,
  CircularProgress,
  Alert,
  Button,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Slider,
  Stack,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import ScrollTable from './ui/ScrollTable';
import {
    XAxis, 
    YAxis, 
    ResponsiveContainer, 
    Tooltip,
    ScatterChart,
    Scatter,
    ReferenceLine,
    ReferenceArea,
} from 'recharts';
import MatchHistory from './MatchHistory';
import Matchups from './Matchups';
import ContextualQueryPrompts from './ContextualQueryPrompts';
import MatchPreviewCard from './MatchPreviewCard';
import ExpectStrip from './ExpectStrip';
import useMatchPreview from '../hooks/useMatchPreview';
import PostTossSetup from './PostTossSetup';
import { getVenueContextualQueries } from '../utils/queryBuilderLinks';
import VenueSectionTabs from './VenueSectionTabs';
import VenueNotesDesktopNav from './VenueNotesDesktopNav';
import BoundaryAnalysis from './BoundaryAnalysis';
import ForesightCard from './ForesightCard';
import EmptyState from './ui/EmptyState';
import CollapsibleSection, { openSection } from './ui/CollapsibleSection';
import { ScoresBarChart, WinPercentagesPie } from './venue/VenueResultCharts';
import StoryPreview from './story/StoryPreview';
import { toStoryChapters } from './story/visuals';
import useStoryCards from '../hooks/useStoryCards';

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
                <Box sx={{ bgcolor: hsColors.surface1, p: isMobile ? 1 : 2, border: `1px solid ${hsColors.border}`, borderRadius: 1 }}>
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

/**
 * Venue leaders (most runs / most wickets). One table for both: the two copies had drifted into the
 * same bugs -- overflowX:'hidden' disabled ScrollTable's sideways scroll (wide rows were clipped on
 * phones) and the player's team lived only in a hover `title`, which touch never shows. The team
 * now sits under the name, so the table reads the same on a phone.
 */
const LeadersTable = ({ title, rows, teamKey, columns, isMobile }) => {
    if (!rows || rows.length === 0) return null;
    const cellSx = { px: isMobile ? 0.75 : 1, fontSize: isMobile ? '0.8125rem' : '0.875rem' };

    return (
        <Box>
            <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1 }}>{title}</Typography>
            <ScrollTable stickyFirstColumn>
                <Table size="small">
                    <TableHead>
                        <TableRow>
                            <TableCell sx={cellSx}>Player</TableCell>
                            {columns.map((col) => (
                                <TableCell key={col.label} align="right" sx={{ ...cellSx, whiteSpace: 'nowrap' }}>{col.label}</TableCell>
                            ))}
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {rows.map((row, index) => {
                            const team = String(row[teamKey] || '').split('/').pop().trim();
                            return (
                                <TableRow key={`${row.name}-${index}`}>
                                    <TableCell sx={cellSx}>
                                        <Box sx={{ fontWeight: 600, lineHeight: 1.25 }}>{row.name}</Box>
                                        {team && (
                                            <Box sx={{ fontSize: '0.75rem', color: 'text.secondary', lineHeight: 1.2 }}>{team}</Box>
                                        )}
                                    </TableCell>
                                    {columns.map((col) => (
                                        <TableCell key={col.label} align="right" sx={{ ...cellSx, whiteSpace: 'nowrap', fontVariantNumeric: 'tabular-nums' }}>
                                            {col.render(row)}
                                        </TableCell>
                                    ))}
                                </TableRow>
                            );
                        })}
                    </TableBody>
                </Table>
            </ScrollTable>
        </Box>
    );
};

const fixed = (value, digits) => (value == null || Number.isNaN(Number(value)) ? '–' : Number(value).toFixed(digits));

const BattingLeaders = ({ data, isMobile }) => (
    <LeadersTable
        title="Most runs"
        rows={data}
        teamKey="batting_team"
        isMobile={isMobile}
        columns={[
            { label: 'Inns', render: (r) => r.batInns },
            { label: 'Runs', render: (r) => r.batRuns },
            { label: 'Avg @ SR', render: (r) => `${fixed(r.batAvg, 1)} @ ${fixed(r.batSR, 0)}` },
            { label: 'BPD', render: (r) => fixed(r.batBPD, 1) },
        ]}
    />
);

const BowlingLeaders = ({ data, isMobile }) => (
    <LeadersTable
        title="Most wickets"
        rows={data}
        teamKey="bowling_team"
        isMobile={isMobile}
        columns={[
            { label: 'Inns', render: (r) => r.bowlInns },
            { label: 'Wkts', render: (r) => r.bowlWickets },
            { label: 'Avg @ ER', render: (r) => `${fixed(r.bowlAvg, 1)} @ ${fixed(r.bowlER, 1)}` },
            { label: 'BPD', render: (r) => fixed(r.bowlBPD, 1) },
        ]}
    />
);

const PhaseWiseStrategy = ({ data, isMobile }) => {
    // Phase boundaries come from the selected format, not T20 literals. An ODI splits
    // 0-9/10-24/25-39/40-49 over 50, so the old hardcoded bounds mislabelled every phase and
    // the /20 divisor made the bars overflow the track by 2.5x.
    const { active } = useFormat();
    const phases4 = (active?.phases_4?.length ? active.phases_4 : [
        { key: 'powerplay', start_over: 0, end_over: 5 },
        { key: 'middle1', start_over: 6, end_over: 9 },
        { key: 'middle2', start_over: 10, end_over: 14 },
        { key: 'death', start_over: 15, end_over: 19 },
    ]);
    // end_over is inclusive; the exclusive edge is +1, which is what the widths need.
    const PHASE_OVERS = phases4.map((p) => ({
        start: p.start_over,
        end: p.end_over + 1,
        label: p.key,
    }));
    const totalOvers = PHASE_OVERS.length ? PHASE_OVERS[PHASE_OVERS.length - 1].end : 20;

    const processPhaseData = (phaseStats) => {
        if (!phaseStats) return [];
        
        return PHASE_OVERS.map(phase => ({
            ...phase,
            width: ((phase.end - phase.start) / totalOvers) * 100,
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
                    backgroundColor: hsColors.surface2,
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
                                // Deeper tones than the old #5a8691/#55ae6a, which left white text at ~2.6:1.
                                backgroundColor: index % 2 === 0 ? '#35606a' : '#2f6e45',
                                color: '#fff',
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
                                fontSize: isMobile ? '0.7rem' : '0.75rem',
                                color: 'text.secondary',
                                borderRight: index < phaseData.length - 1 ? `1px solid ${hsColors.border}` : 'none'
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
        <Box sx={{ mt: isMobile ? 0.25 : 2, width: '100%', px: { xs: 1.5, sm: 0 } }}>
            <Typography variant={isMobile ? "h6" : "h5"} gutterBottom>Phase-wise Strategy</Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: isMobile ? 2 : 3 }}>
                {renderPhase(firstInningsData, "Batting First")}
                {renderPhase(secondInningsData, "Chasing")}
            </Box>
        </Box>
    );
};

const MONTH_YEAR_FORMATTER = new Intl.DateTimeFormat('en-US', {
    month: 'short',
    year: 'numeric',
});

const parseDateString = (dateString) => {
    if (!dateString) {
        return null;
    }

    const [year, month, day] = dateString.split('-').map((part) => Number.parseInt(part, 10));
    if (!year || !month || !day) {
        return null;
    }

    return new Date(year, month - 1, day);
};

const formatVenueDateRange = (startDate, endDate) => {
    const start = parseDateString(startDate);
    const end = parseDateString(endDate);

    if (!start || !end) {
        return `${startDate} - ${endDate}`;
    }

    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const normalizedEnd = new Date(end);
    normalizedEnd.setHours(0, 0, 0, 0);

    const startLabel = MONTH_YEAR_FORMATTER.format(start);
    const endLabel = normalizedEnd.getTime() === today.getTime()
        ? 'Today'
        : MONTH_YEAR_FORMATTER.format(end);

    if (startLabel === endLabel) {
        return startLabel;
    }

    return `${startLabel} - ${endLabel}`;
};

// "14 T20s", "1 ODI" -- the header count used to say "T20s" whatever the format.
const matchNoun = (format, count) => {
    const noun = format === 'ODI' ? 'ODI' : format === 'TEST' ? 'Test' : 'T20';
    return count === 1 ? noun : `${noun}s`;
};

const VenueNotes = ({
    venue,
    startDate,
    endDate,
    venueStats,
    statsData,
    selectedTeam1,
    selectedTeam2,
    matchHistory,
    filtersExpanded,
    onToggleFilters,
    isMobile,
    leagues = [],
    includeInternational = false,
    topTeams = null,
    dayNightFilter = 'all',
    onDayNightFilterChange = null,
    espnEventId = null,
  }) => {

    // The preview is one format's record. Post-toss XI analysis (impact subs, T20 fantasy
    // scoring) and Foresight (IPL-trained models) are men's-T20-only, so other formats hide them.
    const { pinnedFormatParams, active: activeFormat } = useFormat();
    // The venue page keeps its selections in state, so the address bar can be just /venue?fmt=...
    // Share a link that reopens this exact preview instead.
    const shareUrl = useMemo(() => {
        const params = new URLSearchParams();
        if (venue) params.set('venue', venue);
        if (selectedTeam1?.full_name) params.set('team1', selectedTeam1.full_name);
        if (selectedTeam2?.full_name) params.set('team2', selectedTeam2.full_name);
        if (dayNightFilter && dayNightFilter !== 'all') params.set('dayNight', dayNightFilter);
        params.set('autoload', 'true');
        if (activeFormat?.slug && activeFormat.slug !== 'all') params.set('fmt', activeFormat.slug);
        return `${window.location.origin}/venue?${params.toString()}`;
    }, [venue, selectedTeam1?.full_name, selectedTeam2?.full_name, dayNightFilter, activeFormat?.slug]);
    const isT20Preview = pinnedFormatParams.format === 'T20' && pinnedFormatParams.gender === 'male';
    const formatSlug = `${pinnedFormatParams.gender === 'male' ? 'mens' : 'womens'}-${pinnedFormatParams.format.toLowerCase()}`;

    // One-line takeaways for the folded section headers on phones.
    const venueTakeaway = (() => {
        const total = venueStats?.total_matches || 0;
        if (!total) return undefined;
        const batFirst = venueStats.batting_first_wins || 0;
        const chase = venueStats.batting_second_wins || 0;
        return `Batting first ${batFirst}, chasing ${chase} of ${total}`;
    })();
    const leadersTakeaway = (() => {
        const bat = statsData?.batting_leaders?.[0];
        const bowl = statsData?.bowling_leaders?.[0];
        const parts = [];
        if (bat) parts.push(`${bat.name}: ${bat.batRuns} runs`);
        if (bowl) parts.push(`${bowl.name}: ${bowl.bowlWickets} wickets`);
        return parts.join(' · ') || undefined;
    })();

    const [activeSectionId, setActiveSectionId] = useState('summary');
    const [activatedSections, setActivatedSections] = useState(() => new Set(['expect', 'summary', 'preview', 'teams']));
    const [postTossSelection, setPostTossSelection] = useState(null);
    const sectionRefs = useRef({});
    const foresightEnabled = activeSectionId === 'foresight' || activatedSections.has('foresight');
    const previewEnabled = activeSectionId === 'preview' || activatedSections.has('preview');
    const teamsEnabled = activeSectionId === 'teams' || activatedSections.has('teams');
    const boundariesEnabled = activeSectionId === 'boundaries' || activatedSections.has('boundaries');

    useEffect(() => {
        setPostTossSelection(null);
    }, [selectedTeam1?.full_name, selectedTeam2?.full_name, venue, startDate, endDate, dayNightFilter]);

    const handlePostTossApply = useCallback((nextData) => {
        setPostTossSelection({
            team1Xi: nextData?.team1_xi || [],
            team2Xi: nextData?.team2_xi || [],
            xpointsPostToss: nextData?.xpoints_post_toss || {},
            xpointsBase: nextData?.xpoints_base || {},
            xpointsDelta: nextData?.xpoints_delta || {},
            playerDrillLinks: nextData?.player_drill_links || {},
            raw: nextData || null,
        });
    }, []);

    // A venue can have zero matches under the current filters (a new ground, a narrow date
    // window, or internationals restricted to the top N sides). Rendering the venue sections then
    // produced a page of 0s and 0-0 bars, so show one explanation instead and keep only the
    // sections that are about the two teams rather than the ground.
    const noVenueMatches = Boolean(venueStats)
        && venue !== 'All Venues'
        && (venueStats.total_matches || 0) === 0;

    // One preview request feeds both the "What to expect" strip and the (folded) written preview.
    const previewState = useMatchPreview({
        venue,
        team1: selectedTeam1?.full_name || selectedTeam1?.abbreviated_name,
        team2: selectedTeam2?.full_name || selectedTeam2?.abbreviated_name,
        startDate,
        endDate,
        // The page's own filters, so the strip and the venue summary count the same matches.
        // (The endpoint has no leagues filter; with leagues selected the strip covers all leagues.)
        includeInternational: Boolean(includeInternational),
        topTeams: topTeams || 20,
        dayNightFilter,
        enabled: Boolean(selectedTeam1 && selectedTeam2),
    });
    const expectBlock = previewState.data?.expect || null;

    const sectionGroups = useMemo(() => {
        const emptyReasons = [
            startDate ? 'The date range may be too narrow — matches before it are excluded.' : null,
            leagues?.length ? 'Only the selected leagues are included.' : null,
            includeInternational && topTeams
                ? `Internationals are limited to the top ${topTeams} teams, so games between other sides are left out.`
                : null,
            !includeInternational ? 'International matches are excluded.' : null,
        ].filter(Boolean);

        const groups = [
            // 1. SUMMARY — venue stats at a glance
            {
                id: 'summary',
                label: 'Summary',
                defaultOpen: !(selectedTeam1 && selectedTeam2),
                takeaway: venueTakeaway,
                content: noVenueMatches ? (
                    <EmptyState
                        title={`No matches at ${venue} for these filters`}
                        description={selectedTeam1 && selectedTeam2
                            ? 'There is no venue history to summarise yet. Team form and head-to-head below still apply.'
                            : 'There is no venue history to summarise yet.'}
                        reasons={emptyReasons}
                        actionLabel={onToggleFilters ? 'Edit filters' : undefined}
                        onAction={onToggleFilters}
                    />
                ) : (
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                        <WinPercentagesPie data={venueStats} />
                        <ScoresBarChart data={venueStats} />
                        <PhaseWiseStrategy data={venueStats} isMobile={isMobile} />
                    </Box>
                ),
            },
        ];

        // What to expect: the preview's numbers, first and open (needs both teams).
        if (selectedTeam1 && selectedTeam2 && (expectBlock || previewState.loading)) {
            groups.unshift({
                id: 'expect',
                label: 'What to expect',
                defaultOpen: true,
                takeaway: expectBlock?.lean?.label || 'Par score, toss, form and head to head',
                content: expectBlock ? (
                    <ExpectStrip
                        expect={expectBlock}
                        team1={selectedTeam1.full_name}
                        team2={selectedTeam2.full_name}
                    />
                ) : (
                    <Box sx={{ p: 3, display: 'flex', justifyContent: 'center' }}><CircularProgress size={24} /></Box>
                ),
            });
        }

        // 2. AI PREVIEW (only when both teams selected)
        if (selectedTeam1 && selectedTeam2) {
            groups.push({
                id: 'preview',
                label: 'Full preview',
                takeaway: previewState.data?.headline || 'Written preview: venue, form, head to head, key players',
                content: (
                    <MatchPreviewCard
                        venue={venue}
                        team1Identifier={selectedTeam1.full_name || selectedTeam1.abbreviated_name}
                        team2Identifier={selectedTeam2.full_name || selectedTeam2.abbreviated_name}
                        startDate={startDate}
                        endDate={endDate}
                        includeInternational
                        topTeams={20}
                        enabled={previewEnabled}
                        isMobile={isMobile}
                        dayNightFilter={dayNightFilter}
                        onDayNightFilterChange={onDayNightFilterChange}
                        previewState={previewState}
                    />
                ),
            });
        }

        // 3. TEAMS (H2H + history + matchups — only when both teams selected)
        if (selectedTeam1 && selectedTeam2) {
            groups.push({
                id: 'teams',
                label: 'Teams',
                defaultOpen: true,
                takeaway: 'Head to head, form, playing XIs and batter v bowler matchups',
                content: (
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                        {matchHistory ? (
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
                        ) : (
                            <Box sx={{ p: 2, textAlign: 'center' }}>
                                <CircularProgress size={24} />
                            </Box>
                        )}
                        {isT20Preview ? (
                        <PostTossSetup
                            venue={venue}
                            team1Identifier={selectedTeam1.full_name || selectedTeam1.abbreviated_name}
                            team2Identifier={selectedTeam2.full_name || selectedTeam2.abbreviated_name}
                            dayNightFilter={dayNightFilter}
                            isMobile={isMobile}
                            onApplyResult={handlePostTossApply}
                            espnEventId={espnEventId}
                        />
                        ) : (
                            <Typography variant="body2" color="text.secondary" sx={{ px: 0.5 }}>
                                Post-toss XI analysis and fantasy projections are available for men&apos;s T20 only.
                            </Typography>
                        )}
                        <Matchups
                            team1={selectedTeam1.full_name}
                            team2={selectedTeam2.full_name}
                            venue={venue}
                            startDate={startDate}
                            endDate={endDate}
                            team1_players={postTossSelection?.team1Xi || []}
                            team2_players={postTossSelection?.team2Xi || []}
                            postTossXpoints={postTossSelection?.xpointsPostToss || {}}
                            postTossDelta={postTossSelection?.xpointsDelta || {}}
                            postTossRaw={postTossSelection?.raw || null}
                            postTossPlayerDrillLinks={postTossSelection?.playerDrillLinks || {}}
                            dayNightFilter={dayNightFilter}
                            enabled={teamsEnabled}
                            isMobile={isMobile}
                        />
                    </Box>
                ),
            });
        }

        // 5.5 BOUNDARIES
        groups.push({
            id: 'boundaries',
            label: 'Boundaries',
            takeaway: 'How often boundaries come against pace and spin, by phase',
            content: (
                <BoundaryAnalysis
                    context="venue"
                    name={venue}
                    startDate={startDate}
                    endDate={endDate}
                    leagues={leagues}
                    includeInternational={includeInternational}
                    topTeams={topTeams}
                    isMobile={isMobile}
                    enabled={boundariesEnabled}
                />
            ),
        });

        // 6. LEADERS
        if (statsData?.batting_leaders?.length > 0 || statsData?.bowling_leaders?.length > 0) {
            groups.push({
                id: 'leaders',
                label: 'Leaders',
                takeaway: leadersTakeaway,
                content: (
                    <Grid container spacing={isMobile ? 2 : 3}>
                        {statsData?.batting_leaders?.length > 0 && (
                            <Grid item xs={12} md={6}>
                                <BattingLeaders data={statsData.batting_leaders} isMobile={isMobile} />
                            </Grid>
                        )}
                        {statsData?.bowling_leaders?.length > 0 && (
                            <Grid item xs={12} md={6}>
                                <BowlingLeaders data={statsData.bowling_leaders} isMobile={isMobile} />
                            </Grid>
                        )}
                    </Grid>
                ),
            });
        }

        // 7. EXPLORE
        groups.push({
            id: 'explore',
            label: 'Explore',
            takeaway: 'Ready-made questions to open in the query builder',
            content: (
                <ContextualQueryPrompts
                    queries={getVenueContextualQueries(venue, {
                        startDate,
                        endDate,
                        leagues: [],
                        team1: selectedTeam1,
                        team2: selectedTeam2,
                        fmt: formatSlug,
                    })}
                    title={`Explore ${venue.split(',')[0]} Data`}
                />
            ),
        });

        // 9. ML FORESIGHT (last section, only when both teams selected; models are T20-only)
        if (selectedTeam1 && selectedTeam2 && isT20Preview) {
            groups.push({
                id: 'foresight',
                label: 'Foresight',
                takeaway: 'Model forecast: win probability and predicted scores',
                content: (
                    <ForesightCard
                        venue={venue}
                        team1={selectedTeam1.full_name || selectedTeam1.abbreviated_name}
                        team2={selectedTeam2.full_name || selectedTeam2.abbreviated_name}
                        enabled={foresightEnabled}
                        isMobile={isMobile}
                    />
                ),
            });
        }

        if (noVenueMatches) {
            // Sections built on the ground's own history have nothing to show.
            const teamSections = new Set(['expect', 'summary', 'preview', 'teams', 'foresight']);
            return groups.filter((group) => teamSections.has(group.id));
        }
        return groups;
    }, [
        venueTakeaway,
        leadersTakeaway,
        expectBlock,
        previewState,
        isT20Preview,
        formatSlug,
        noVenueMatches,
        onToggleFilters,
        venueStats,
        statsData,
        selectedTeam1,
        selectedTeam2,
        venue,
        startDate,
        endDate,
        matchHistory,
        isMobile,
        leagues,
        includeInternational,
        topTeams,
        foresightEnabled,
        previewEnabled,
        teamsEnabled,
        boundariesEnabled,
        postTossSelection,
        handlePostTossApply,
        dayNightFilter,
        onDayNightFilterChange,
        espnEventId,
    ]);

    const formattedDateRange = useMemo(() => formatVenueDateRange(startDate, endDate), [startDate, endDate]);

    const markSectionActivated = useCallback((sectionId) => {
        if (!sectionId) return;
        setActivatedSections((previous) => {
            if (previous.has(sectionId)) {
                return previous;
            }
            const next = new Set(previous);
            next.add(sectionId);
            return next;
        });
    }, []);

    const handleSectionSelect = useCallback((sectionId) => {
        markSectionActivated(sectionId);
        setActiveSectionId(sectionId);
        if (isMobile) {
            // Opens the folded section, then scrolls to it.
            openSection(`section-${sectionId}`);
            return;
        }
        const sectionElement = sectionRefs.current[sectionId];
        if (sectionElement) {
            sectionElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }, [markSectionActivated, isMobile]);

    useEffect(() => {
        setActiveSectionId('summary');
        setActivatedSections(new Set(['expect', 'summary', 'preview', 'teams']));
    }, [selectedTeam1, selectedTeam2, venue]);

    useEffect(() => {
        if (!sectionGroups.length) {
            return undefined;
        }

        const visibleSections = new Map();
        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                const sectionId = entry.target.dataset.sectionId;
                if (!sectionId) {
                    return;
                }
                if (entry.isIntersecting) {
                    visibleSections.set(sectionId, entry.intersectionRatio);
                    markSectionActivated(sectionId);
                } else {
                    visibleSections.delete(sectionId);
                }
            });

            const nextActive = [...visibleSections.entries()].sort((a, b) => b[1] - a[1])[0]?.[0];
            if (nextActive) {
                setActiveSectionId(nextActive);
            }
        }, {
            rootMargin: '0px 0px 0px 0px',
            threshold: [0.1, 0.35, 0.6],
        });

        sectionGroups.forEach((group) => {
            const element = sectionRefs.current[group.id];
            if (element) {
                observer.observe(element);
            }
        });

        return () => observer.disconnect();
    }, [sectionGroups, markSectionActivated]);

    const renderSectionContent = useCallback((section) => {
        const shouldRender = section.id === 'summary'
            || section.id === activeSectionId
            || activatedSections.has(section.id);

        if (shouldRender) {
            return section.content;
        }

        return (
            <Box sx={{ p: 3, display: 'flex', justifyContent: 'center' }}>
                <CircularProgress size={24} />
            </Box>
        );
    }, [activeSectionId, activatedSections]);

// Story-style preview (MATCH_PREVIEW_VIZ_PLAN.md), behind ?story=1 until the switch-over.
const storyMode = new URLSearchParams(window.location.search).get('story') === '1';
// One request for every card (services/preview_cards), with the page's own filters.
const storyState = useStoryCards({
    venue,
    team1: selectedTeam1?.full_name || selectedTeam1?.abbreviated_name,
    team2: selectedTeam2?.full_name || selectedTeam2?.abbreviated_name,
    team1Short: selectedTeam1?.abbreviated_name,
    team2Short: selectedTeam2?.abbreviated_name,
    startDate,
    endDate,
    includeInternational: Boolean(includeInternational),
    topTeams: topTeams || 20,
    dayNightFilter,
    enabled: storyMode && Boolean(selectedTeam1 && selectedTeam2),
});
const storyChapters = useMemo(
    () => toStoryChapters(storyState.data, { isMobile }),
    [storyState.data, isMobile],
);

if (!venueStats) return <Alert severity="info">Please select a venue</Alert>;

const classicPage = (
    <Box sx={{ mx: { xs: -1, sm: 0 }, p: { xs: 0, sm: 2 } }}>
        <Box
            sx={{
                mb: { xs: 0.5, sm: 2.5 },
                px: { xs: 1.5, sm: 3 },
                py: { xs: 0.5, sm: 2.5 },
                border: isMobile ? 'none' : '1px solid',
                borderColor: 'divider',
                borderRadius: isMobile ? 0 : 3,
                boxShadow: isMobile ? 'none' : 1,
                bgcolor: isMobile ? 'transparent' : 'background.paper',
                // Was a literal white gradient, which bypassed the scoped dark theme and left the
                // light venue title invisible on white.
                backgroundImage: 'none',
            }}
        >
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1.5 }}>
                <Typography
                    variant={isMobile ? "h6" : "h4"}
                    sx={{
                        fontWeight: 700,
                        lineHeight: 1.15,
                        flex: 1,
                        minWidth: 0,
                    }}
                >
                    {venue === "All Venues" ? 'All Venues' : venue}
                </Typography>
                {onToggleFilters ? (
                    <Button
                        size="small"
                        variant="text"
                        onClick={onToggleFilters}
                        sx={{
                            minWidth: 'auto',
                            px: 0.5,
                            py: 0.25,
                            textTransform: 'none',
                            fontWeight: 700,
                            flexShrink: 0,
                        }}
                    >
                        {filtersExpanded ? 'Hide filters' : 'Edit filters'}
                    </Button>
                ) : null}
                <ShareButton variant="icon" kind="preview" title={`${venue} preview on Hindsight`} url={shareUrl} sx={{ flexShrink: 0 }} />
            </Box>
            <Box sx={{ mt: 0.25, px: 0.1 }}>
                <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600 }}>
                    {`${venueStats.total_matches} ${matchNoun(pinnedFormatParams.format, venueStats.total_matches)} • ${formattedDateRange}`}
                </Typography>
            </Box>
        </Box>

        {isMobile ? (
            <>
                <VenueSectionTabs
                    sections={sectionGroups.map(({ id, label }) => ({ id, label }))}
                    activeSectionId={activeSectionId}
                    onSectionSelect={handleSectionSelect}
                />
                {/* Phones: every section folds to its title and a one-line takeaway, and only the
                    ones that answer "what to expect" start open. A section mounts (and fetches) the
                    first time it is opened. */}
                <Box sx={{ display: 'flex', flexDirection: 'column', px: 1, pb: 2 }}>
                    {sectionGroups.map((section) => (
                        <Box
                            key={section.id}
                            ref={(el) => { sectionRefs.current[section.id] = el; }}
                            data-section-id={section.id}
                        >
                            <CollapsibleSection
                                id={`section-${section.id}`}
                                title={section.label}
                                takeaway={section.takeaway}
                                defaultOpen={Boolean(section.defaultOpen)}
                            >
                                {renderSectionContent(section)}
                            </CollapsibleSection>
                        </Box>
                    ))}
                </Box>
            </>
        ) : (
            <Box
                sx={{
                    display: 'grid',
                    gridTemplateColumns: '240px minmax(0, 1fr)',
                    gap: 3,
                    alignItems: 'start',
                }}
            >
                <VenueNotesDesktopNav
                    sections={sectionGroups.map(({ id, label }) => ({ id, label }))}
                    activeSectionId={activeSectionId}
                    onSectionSelect={handleSectionSelect}
                />
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                    {sectionGroups.map((section) => (
                        <Box
                            key={section.id}
                            ref={(element) => {
                                sectionRefs.current[section.id] = element;
                            }}
                            data-section-id={section.id}
                            sx={{ scrollMarginTop: '88px' }}
                        >
                            <Card
                                sx={{
                                    p: 3,
                                    borderRadius: 3,
                                    border: '1px solid',
                                    borderColor: 'divider',
                                    boxShadow: 1,
                                }}
                            >
                                <Typography variant="h5" sx={{ mb: 2.5, fontWeight: 700 }}>
                                    {section.label}
                                </Typography>
                                {renderSectionContent(section)}
                            </Card>
                        </Box>
                    ))}
                </Box>
            </Box>
        )}
    </Box>
);

if (storyMode) {
    const fixture = selectedTeam1 && selectedTeam2
        ? `${selectedTeam1.abbreviated_name} v ${selectedTeam2.abbreviated_name} · ${venue.split(',')[0]}`
        : venue;
    return (
        <StoryPreview
            chapters={storyChapters}
            loading={storyState.loading}
            fixtureLabel={fixture}
            onSettings={onToggleFilters}
            classicPage={classicPage}
        />
    );
}
return classicPage;
};

export default VenueNotes;
