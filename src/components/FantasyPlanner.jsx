import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
    Box,
    Card,
    Typography,
    CircularProgress,
    Alert,
    Button,
    Chip,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    TextField,
    IconButton,
    useMediaQuery,
    useTheme,
    Tabs,
    Tab,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import axios from 'axios';
import config from '../config';

const TEAM_COLORS = {
    CSK: '#eff542', MI: '#42a7f5', RCB: '#f54242', RR: '#FF2AA8',
    KKR: '#610048', PBKS: '#FF004D', SRH: '#FF7C01', LSG: '#00BBB3',
    DC: '#004BC5', GT: '#01295B',
};

// ─── Fixture Calendar (Panel 1) ────────────────────────────────────────────
const FixtureCalendar = ({ fixtures, isMobile, squadTeams }) => {
    if (!fixtures || fixtures.length === 0) return null;

    return (
        <Box sx={{ overflowX: 'auto', pb: 1 }}>
            <Box sx={{ display: 'flex', gap: 1.5, minWidth: 'max-content', px: 1 }}>
                {fixtures.map((f) => {
                    const t1Count = (squadTeams || []).filter(t => t === f.team1).length;
                    const t2Count = (squadTeams || []).filter(t => t === f.team2).length;
                    return (
                        <Card
                            key={f.match_num}
                            sx={{
                                minWidth: isMobile ? 140 : 160,
                                p: 1.5,
                                border: '1px solid',
                                borderColor: 'divider',
                                borderRadius: 2,
                                flexShrink: 0,
                            }}
                        >
                            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                                Match {f.match_num} &middot; {f.date}
                            </Typography>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.5 }}>
                                <Chip
                                    label={f.team1}
                                    size="small"
                                    sx={{
                                        bgcolor: TEAM_COLORS[f.team1] || '#666',
                                        color: ['CSK', 'LSG'].includes(f.team1) ? '#000' : '#fff',
                                        fontWeight: 700,
                                        fontSize: '0.7rem',
                                    }}
                                />
                                <Typography variant="caption" sx={{ fontWeight: 600 }}>vs</Typography>
                                <Chip
                                    label={f.team2}
                                    size="small"
                                    sx={{
                                        bgcolor: TEAM_COLORS[f.team2] || '#666',
                                        color: ['CSK', 'LSG'].includes(f.team2) ? '#000' : '#fff',
                                        fontWeight: 700,
                                        fontSize: '0.7rem',
                                    }}
                                />
                            </Box>
                            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5, fontSize: '0.65rem' }}>
                                {f.venue?.split(',')[0] || ''}
                            </Typography>
                            {(t1Count > 0 || t2Count > 0) && (
                                <Typography variant="caption" sx={{ display: 'block', mt: 0.25, fontSize: '0.65rem', fontWeight: 600 }}>
                                    Your players: {t1Count + t2Count}
                                </Typography>
                            )}
                        </Card>
                    );
                })}
            </Box>
        </Box>
    );
};

// ─── Squad Builder (Panel 2) ───────────────────────────────────────────────
const SquadBuilder = ({ squad, onRemovePlayer, onAutoPick, loading, transfersUsed, isMobile }) => {
    const roleGroups = useMemo(() => {
        const groups = { WK: [], BAT: [], AR: [], BOWL: [] };
        (squad || []).forEach((p) => {
            const role = p.role || 'BAT';
            if (groups[role]) groups[role].push(p);
            else groups.BAT.push(p);
        });
        return groups;
    }, [squad]);

    return (
        <Card sx={{ p: 2, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                    Squad ({squad?.length || 0}/11)
                </Typography>
                <Button
                    variant="contained"
                    size="small"
                    onClick={onAutoPick}
                    disabled={loading}
                    sx={{ textTransform: 'none', fontWeight: 600 }}
                >
                    {loading ? <CircularProgress size={18} /> : 'Auto-pick'}
                </Button>
            </Box>

            <Box sx={{ display: 'flex', gap: 2, mb: 1 }}>
                <Typography variant="caption" color="text.secondary">
                    Transfers: {transfersUsed}/160
                </Typography>
                <Typography variant="caption" color="text.secondary">
                    Budget: {(squad || []).reduce((sum, p) => sum + (p.credits || 0), 0).toFixed(1)}/100 cr
                </Typography>
            </Box>

            {Object.entries(roleGroups).map(([role, players]) => (
                <Box key={role} sx={{ mb: 1.5 }}>
                    <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary', textTransform: 'uppercase' }}>
                        {role === 'WK' ? 'Wicket-keepers' : role === 'BAT' ? 'Batters' : role === 'BOWL' ? 'Bowlers' : 'All-rounders'} ({players.length})
                    </Typography>
                    {players.map((p) => (
                        <Box
                            key={p.name}
                            sx={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                py: 0.5,
                                borderBottom: '1px solid',
                                borderColor: 'divider',
                            }}
                        >
                            <Box>
                                <Typography variant="body2" sx={{ fontWeight: 600, fontSize: isMobile ? '0.8rem' : '0.875rem' }}>
                                    {p.name}
                                </Typography>
                                <Chip
                                    label={p.team}
                                    size="small"
                                    sx={{
                                        height: 18,
                                        fontSize: '0.6rem',
                                        bgcolor: TEAM_COLORS[p.team] || '#666',
                                        color: ['CSK', 'LSG'].includes(p.team) ? '#000' : '#fff',
                                    }}
                                />
                            </Box>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <Typography variant="body2" sx={{ fontSize: '0.7rem', color: 'text.secondary' }}>
                                    {p.credits || '?'}cr
                                </Typography>
                                <Typography variant="body2" sx={{ fontWeight: 600, fontSize: '0.8rem' }}>
                                    {p.total_expected_points || 0} pts
                                </Typography>
                                <IconButton size="small" onClick={() => onRemovePlayer(p.name)}>
                                    <DeleteIcon fontSize="small" />
                                </IconButton>
                            </Box>
                        </Box>
                    ))}
                </Box>
            ))}

            {(!squad || squad.length === 0) && (
                <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 2 }}>
                    Click "Auto-pick" to generate a recommended squad
                </Typography>
            )}
        </Card>
    );
};

// ─── Recommendations Table (Panel 3) ───────────────────────────────────────
const RecommendationsTable = ({ allPlayers, squad, onAddPlayer, isMobile }) => {
    const [sortBy, setSortBy] = useState('total_expected_points');

    const squadNames = useMemo(() => new Set((squad || []).map(p => p.name)), [squad]);

    const sorted = useMemo(() => {
        return [...(allPlayers || [])].sort((a, b) => (b[sortBy] || 0) - (a[sortBy] || 0));
    }, [allPlayers, sortBy]);

    return (
        <Card sx={{ p: 2, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1.5 }}>
                Player Rankings
            </Typography>
            <TableContainer sx={{ maxHeight: 500 }}>
                <Table size="small" stickyHeader>
                    <TableHead>
                        <TableRow>
                            <TableCell sx={{ fontWeight: 700, fontSize: '0.75rem' }}>Player</TableCell>
                            <TableCell sx={{ fontWeight: 700, fontSize: '0.75rem' }}>Team</TableCell>
                            <TableCell sx={{ fontWeight: 700, fontSize: '0.75rem' }}>Role</TableCell>
                            <TableCell
                                align="right"
                                sx={{ fontWeight: 700, fontSize: '0.75rem', cursor: 'pointer' }}
                                onClick={() => setSortBy('credits')}
                            >
                                Cr {sortBy === 'credits' ? '▼' : ''}
                            </TableCell>
                            <TableCell
                                align="right"
                                sx={{ fontWeight: 700, fontSize: '0.75rem', cursor: 'pointer' }}
                                onClick={() => setSortBy('total_expected_points')}
                            >
                                Exp Pts {sortBy === 'total_expected_points' ? '▼' : ''}
                            </TableCell>
                            <TableCell
                                align="right"
                                sx={{ fontWeight: 700, fontSize: '0.75rem', cursor: 'pointer' }}
                                onClick={() => setSortBy('match_count')}
                            >
                                Matches {sortBy === 'match_count' ? '▼' : ''}
                            </TableCell>
                            <TableCell align="center" sx={{ fontWeight: 700, fontSize: '0.75rem' }}></TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {sorted.map((p) => (
                            <TableRow key={p.name} sx={{ bgcolor: squadNames.has(p.name) ? 'action.selected' : 'inherit' }}>
                                <TableCell sx={{ fontSize: '0.8rem', fontWeight: squadNames.has(p.name) ? 700 : 400 }}>
                                    {p.name}
                                </TableCell>
                                <TableCell>
                                    <Chip
                                        label={p.team}
                                        size="small"
                                        sx={{
                                            height: 18,
                                            fontSize: '0.6rem',
                                            bgcolor: TEAM_COLORS[p.team] || '#666',
                                            color: ['CSK', 'LSG'].includes(p.team) ? '#000' : '#fff',
                                        }}
                                    />
                                </TableCell>
                                <TableCell sx={{ fontSize: '0.75rem' }}>{p.role}</TableCell>
                                <TableCell align="right" sx={{ fontSize: '0.75rem', color: 'text.secondary' }}>
                                    {p.credits || '?'}
                                </TableCell>
                                <TableCell align="right" sx={{ fontSize: '0.8rem', fontWeight: 600 }}>
                                    {p.total_expected_points}
                                </TableCell>
                                <TableCell align="right" sx={{ fontSize: '0.8rem' }}>
                                    {p.match_count}
                                </TableCell>
                                <TableCell align="center">
                                    {!squadNames.has(p.name) && (
                                        <Button
                                            size="small"
                                            variant="outlined"
                                            onClick={() => onAddPlayer(p)}
                                            sx={{ textTransform: 'none', fontSize: '0.7rem', minWidth: 40, py: 0 }}
                                        >
                                            + Add
                                        </Button>
                                    )}
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>
        </Card>
    );
};

// ─── Transfer Plan View ────────────────────────────────────────────────────
const TransferPlanView = ({ plan, isMobile }) => {
    if (!plan || !plan.plan || plan.plan.length === 0) {
        return (
            <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 3 }}>
                Set your current team and click "Auto-pick" to generate a transfer plan
            </Typography>
        );
    }

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Typography variant="caption" color="text.secondary">
                Transfers remaining: {plan.transfers_remaining}/{plan.transfers_remaining + plan.total_transfers_used}
            </Typography>
            {plan.plan.map((gw) => (
                <Card key={gw.gameweek} sx={{ p: 2, border: '1px solid', borderColor: 'divider' }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                        Gameweek {gw.gameweek} &middot; {gw.date_range}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                        Expected: {Math.round(gw.expected_total_points)} pts &middot; Transfers: {gw.transfers_used}
                    </Typography>
                    {gw.transfers_in.length > 0 && (
                        <Box sx={{ mt: 1 }}>
                            <Typography variant="caption" sx={{ fontWeight: 600, color: 'success.main' }}>
                                IN: {gw.transfers_in.join(', ')}
                            </Typography>
                        </Box>
                    )}
                    {gw.transfers_out.length > 0 && (
                        <Box>
                            <Typography variant="caption" sx={{ fontWeight: 600, color: 'error.main' }}>
                                OUT: {gw.transfers_out.join(', ')}
                            </Typography>
                        </Box>
                    )}
                    {gw.captain && (
                        <Typography variant="caption" sx={{ display: 'block', mt: 0.5 }}>
                            C: {gw.captain} &middot; VC: {gw.vice_captain}
                        </Typography>
                    )}
                </Card>
            ))}
        </Box>
    );
};

// ─── Main Fantasy Planner Page ─────────────────────────────────────────────
const FantasyPlanner = ({ isMobile }) => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [schedule, setSchedule] = useState(null);
    const [recommendations, setRecommendations] = useState(null);
    const [squad, setSquad] = useState([]);
    const [transferPlan, setTransferPlan] = useState(null);
    const [matchesAhead, setMatchesAhead] = useState(3);
    const [tab, setTab] = useState(0);

    // Load schedule on mount
    useEffect(() => {
        axios.get(`${config.API_URL}/fantasy-planner/schedule`)
            .then((res) => setSchedule(res.data))
            .catch((err) => console.error('Schedule fetch error:', err));
    }, []);

    const upcomingFixtures = useMemo(() => {
        if (!schedule?.fixtures) return [];
        const today = new Date().toISOString().split('T')[0];
        return schedule.fixtures.filter(f => f.date >= today).slice(0, 15);
    }, [schedule]);

    const squadTeams = useMemo(() => (squad || []).map(p => p.team), [squad]);

    const handleAutoPick = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const currentNames = squad.map(p => p.name).join(',') || undefined;
            const res = await axios.get(`${config.API_URL}/fantasy-planner/recommendations`, {
                params: {
                    matches_ahead: matchesAhead,
                    current_team: currentNames,
                },
            });
            setRecommendations(res.data);
            if (res.data.recommended_squad) {
                setSquad(res.data.recommended_squad);
            }
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to fetch recommendations');
        } finally {
            setLoading(false);
        }
    }, [matchesAhead, squad]);

    const handleFetchTransferPlan = useCallback(async () => {
        if (!squad.length) return;
        try {
            const res = await axios.get(`${config.API_URL}/fantasy-planner/transfer-plan`, {
                params: {
                    current_team: squad.map(p => p.name).join(','),
                    gameweek_start: 1,
                    gameweek_end: 3,
                },
            });
            setTransferPlan(res.data);
        } catch (err) {
            console.error('Transfer plan error:', err);
        }
    }, [squad]);

    const handleRemovePlayer = useCallback((name) => {
        setSquad(prev => prev.filter(p => p.name !== name));
    }, []);

    const handleAddPlayer = useCallback((player) => {
        if (squad.length >= 11) return;
        if (squad.some(p => p.name === player.name)) return;
        setSquad(prev => [...prev, {
            name: player.name,
            team: player.team,
            role: player.role,
            total_expected_points: player.total_expected_points,
            match_count: player.match_count,
            matches: [],
        }]);
    }, [squad]);

    return (
        <Box sx={{ py: 2, px: { xs: 1, sm: 2 } }}>
            <Typography variant={isMobile ? "h5" : "h4"} sx={{ fontWeight: 700, mb: 0.5 }}>
                Fantasy Team Planner
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                IPL 2026 &middot; Optimize your fantasy.iplt20.com squad across upcoming matches
            </Typography>

            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

            {/* Fixture Calendar */}
            <Card sx={{ p: 2, mb: 2, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                    <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                        Upcoming Fixtures
                    </Typography>
                    <TextField
                        label="Matches ahead"
                        type="number"
                        size="small"
                        value={matchesAhead}
                        onChange={(e) => setMatchesAhead(Math.max(1, Math.min(20, parseInt(e.target.value) || 3)))}
                        sx={{ width: 120 }}
                        inputProps={{ min: 1, max: 20 }}
                    />
                </Box>
                <FixtureCalendar
                    fixtures={upcomingFixtures}
                    isMobile={isMobile}
                    squadTeams={squadTeams}
                />
            </Card>

            {/* Tabs for Squad / Recommendations / Transfer Plan */}
            <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
                <Tab label="Squad Builder" sx={{ textTransform: 'none', fontWeight: 600 }} />
                <Tab label="Player Rankings" sx={{ textTransform: 'none', fontWeight: 600 }} />
                <Tab label="Transfer Plan" sx={{ textTransform: 'none', fontWeight: 600 }} />
            </Tabs>

            {tab === 0 && (
                <SquadBuilder
                    squad={squad}
                    onRemovePlayer={handleRemovePlayer}
                    onAutoPick={handleAutoPick}
                    loading={loading}
                    transfersUsed={recommendations?.transfers_needed || 0}
                    isMobile={isMobile}
                />
            )}

            {tab === 1 && (
                <RecommendationsTable
                    allPlayers={recommendations?.all_players || []}
                    squad={squad}
                    onAddPlayer={handleAddPlayer}
                    isMobile={isMobile}
                />
            )}

            {tab === 2 && (
                <Card sx={{ p: 2, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
                        <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>Transfer Plan</Typography>
                        <Button
                            variant="outlined"
                            size="small"
                            onClick={handleFetchTransferPlan}
                            disabled={!squad.length}
                            sx={{ textTransform: 'none' }}
                        >
                            Generate Plan
                        </Button>
                    </Box>
                    <TransferPlanView plan={transferPlan} isMobile={isMobile} />
                </Card>
            )}

            {/* Captain / VC suggestions */}
            {recommendations?.captain && (
                <Card sx={{ p: 2, mt: 2, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.5 }}>
                        Captaincy Picks
                    </Typography>
                    <Typography variant="body2">
                        Captain: <strong>{recommendations.captain}</strong> (highest single-match expected points)
                    </Typography>
                    <Typography variant="body2">
                        Vice-captain: <strong>{recommendations.vice_captain}</strong>
                    </Typography>
                </Card>
            )}
        </Box>
    );
};

export default FantasyPlanner;
