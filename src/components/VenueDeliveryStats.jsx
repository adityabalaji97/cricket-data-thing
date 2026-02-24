import React, { useEffect, useState } from 'react';
import axios from 'axios';
import {
    Box,
    Card,
    CircularProgress,
    Tab,
    Tabs,
    Typography,
    Alert
} from '@mui/material';
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Cell,
    Legend
} from 'recharts';
import config from '../config';

const TAB_KEYS = ['length', 'line', 'shot', 'phase'];

const srColor = (sr) => {
    if (sr >= 170) return '#0b8457';
    if (sr >= 145) return '#2a9d8f';
    if (sr >= 120) return '#e9c46a';
    if (sr >= 100) return '#f4a261';
    return '#e76f51';
};

const pct = (value) => (value == null ? 'N/A' : `${Number(value).toFixed(1)}%`);

const VenueDeliveryStats = ({
    venue,
    startDate,
    endDate,
    team1,
    team2,
    isMobile,
    leagues = [],
    includeInternational = false
}) => {
    const [tab, setTab] = useState(0);
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!venue) return;

        const fetchData = async () => {
            setLoading(true);
            setError(null);

            try {
                const params = new URLSearchParams();
                if (startDate) params.append('start_date', startDate);
                if (endDate) params.append('end_date', endDate);
                if (team1) params.append('team1', team1);
                if (team2) params.append('team2', team2);
                if (includeInternational) params.append('include_international', 'true');
                leagues.forEach((league) => params.append('leagues', league));

                const response = await axios.get(
                    `${config.API_URL}/venues/${encodeURIComponent(venue)}/delivery-stats?${params.toString()}`
                );
                setData(response.data);
            } catch (err) {
                console.error('Error fetching venue delivery stats:', err);
                setError('Failed to load delivery stats');
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [venue, startDate, endDate, team1, team2, includeInternational, leagues]);

    if (loading) {
        return (
            <Card sx={{ p: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <CircularProgress size={18} />
                    <Typography variant="body2">Loading delivery stats...</Typography>
                </Box>
            </Card>
        );
    }

    if (error) {
        return <Alert severity="warning">{error}</Alert>;
    }

    if (!data || !data.data_coverage) {
        return null;
    }

    if ((data.data_coverage.matches_covered || 0) < 3) {
        return null;
    }

    const lengthData = (data.length_distribution || []).map((row) => ({
        name: row.label,
        percentage: row.percentage || 0,
        strikeRate: row.strike_rate || 0,
        balls: row.balls || 0,
        runs: row.runs || 0,
        wickets: row.wickets || 0,
        control: row.control_percentage
    }));

    const lineData = (data.line_distribution || []).map((row) => ({
        name: row.label,
        percentage: row.percentage || 0,
        strikeRate: row.strike_rate || 0,
        balls: row.balls || 0,
        runs: row.runs || 0,
        wickets: row.wickets || 0,
        control: row.control_percentage
    }));

    const shotData = [...(data.shot_distribution || [])]
        .sort((a, b) => (b.strike_rate || 0) - (a.strike_rate || 0))
        .slice(0, 12)
        .map((row) => ({
            name: row.label,
            strikeRate: row.strike_rate || 0,
            balls: row.balls || 0,
            runs: row.runs || 0,
            control: row.control_percentage
        }));

    const phaseData = (data.control_by_phase || []).map((row) => ({
        phase: row.phase,
        control: row.control_percentage || 0,
        strikeRate: row.strike_rate || 0,
        balls: row.total_balls || 0
    }));

    const renderEmpty = (label) => (
        <Box sx={{ py: 3 }}>
            <Typography variant="body2" color="text.secondary">
                Not enough tagged {label.toLowerCase()} data for this venue/filter.
            </Typography>
        </Box>
    );

    const MetricTooltip = ({ active, payload, label }) => {
        if (!active || !payload || !payload.length) return null;
        const row = payload[0].payload;
        return (
            <Box sx={{ bgcolor: 'background.paper', border: '1px solid #ddd', p: 1.25, borderRadius: 1 }}>
                <Typography variant="subtitle2">{label || row.name || row.phase}</Typography>
                {'percentage' in row && <Typography variant="body2">% Deliveries: {pct(row.percentage)}</Typography>}
                {'balls' in row && <Typography variant="body2">Balls: {row.balls}</Typography>}
                {'runs' in row && <Typography variant="body2">Runs: {row.runs}</Typography>}
                {'wickets' in row && <Typography variant="body2">Wkts: {row.wickets}</Typography>}
                {'control' in row && <Typography variant="body2">Control%: {pct(row.control)}</Typography>}
                {'strikeRate' in row && <Typography variant="body2">SR: {Number(row.strikeRate || 0).toFixed(1)}</Typography>}
            </Box>
        );
    };

    return (
        <Card sx={{ p: { xs: 1.5, sm: 2 } }}>
            <Typography variant={isMobile ? 'subtitle1' : 'h6'} gutterBottom>
                Delivery Pattern Stats
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                {data.data_coverage.matches_covered} matches, {data.data_coverage.total_balls} balls tracked
            </Typography>

            <Tabs
                value={tab}
                onChange={(e, value) => setTab(value)}
                variant={isMobile ? 'scrollable' : 'standard'}
                scrollButtons="auto"
                sx={{ mb: 1 }}
            >
                <Tab label="Length" />
                <Tab label="Line" />
                <Tab label="Shots" />
                <Tab label="Control by Phase" />
            </Tabs>

            {TAB_KEYS[tab] === 'length' && (
                <>
                    {lengthData.length === 0 ? renderEmpty('length') : (
                        <Box sx={{ height: isMobile ? 320 : 380 }}>
                            <ResponsiveContainer>
                                <BarChart data={lengthData} layout="vertical" margin={{ left: 8, right: 16 }}>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis type="number" tickFormatter={(v) => `${v}%`} />
                                    <YAxis type="category" dataKey="name" width={isMobile ? 105 : 145} tick={{ fontSize: isMobile ? 10 : 12 }} />
                                    <Tooltip content={<MetricTooltip />} />
                                    <Bar dataKey="percentage" name="% Deliveries">
                                        {lengthData.map((entry) => (
                                            <Cell key={entry.name} fill={srColor(entry.strikeRate)} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </Box>
                    )}
                </>
            )}

            {TAB_KEYS[tab] === 'line' && (
                <>
                    {lineData.length === 0 ? renderEmpty('line') : (
                        <Box sx={{ height: isMobile ? 340 : 400 }}>
                            <ResponsiveContainer>
                                <BarChart data={lineData} layout="vertical" margin={{ left: 8, right: 16 }}>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis type="number" tickFormatter={(v) => `${v}%`} />
                                    <YAxis type="category" dataKey="name" width={isMobile ? 110 : 150} tick={{ fontSize: isMobile ? 10 : 12 }} />
                                    <Tooltip content={<MetricTooltip />} />
                                    <Bar dataKey="percentage" name="% Deliveries">
                                        {lineData.map((entry) => (
                                            <Cell key={entry.name} fill={srColor(entry.strikeRate)} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </Box>
                    )}
                </>
            )}

            {TAB_KEYS[tab] === 'shot' && (
                <>
                    {shotData.length === 0 ? renderEmpty('shot') : (
                        <Box sx={{ height: isMobile ? 360 : 420 }}>
                            <ResponsiveContainer>
                                <BarChart data={shotData} layout="vertical" margin={{ left: 8, right: 16 }}>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis type="number" />
                                    <YAxis type="category" dataKey="name" width={isMobile ? 120 : 170} tick={{ fontSize: isMobile ? 10 : 12 }} />
                                    <Tooltip content={<MetricTooltip />} />
                                    <Bar dataKey="strikeRate" name="Strike Rate">
                                        {shotData.map((entry) => (
                                            <Cell key={entry.name} fill={srColor(entry.strikeRate)} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </Box>
                    )}
                </>
            )}

            {TAB_KEYS[tab] === 'phase' && (
                <>
                    {phaseData.length === 0 ? renderEmpty('phase') : (
                        <Box sx={{ height: isMobile ? 320 : 360 }}>
                            <ResponsiveContainer>
                                <BarChart data={phaseData}>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis dataKey="phase" />
                                    <YAxis />
                                    <Tooltip content={<MetricTooltip />} />
                                    <Legend />
                                    <Bar dataKey="control" name="Control %" fill="#2a9d8f" />
                                    <Bar dataKey="strikeRate" name="Strike Rate" fill="#e76f51" />
                                </BarChart>
                            </ResponsiveContainer>
                        </Box>
                    )}
                </>
            )}
        </Card>
    );
};

export default VenueDeliveryStats;
