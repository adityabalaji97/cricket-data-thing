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
    Tabs,
    Tab,
    Autocomplete,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import axios from 'axios';
import config from '../config';
import CondensedName from './common/CondensedName';
import { getTeamAbbr } from '../utils/teamAbbreviations';

const TEAM_COLORS = {
    CSK: '#eff542', MI: '#42a7f5', RCB: '#f54242', RR: '#FF2AA8',
    KKR: '#610048', PBKS: '#FF004D', SRH: '#FF7C01', LSG: '#00BBB3',
    DC: '#004BC5', GT: '#01295B',
};

const RECOMMENDATION_RETRY_DELAYS_MS = process.env.NODE_ENV === 'test' ? [0, 1, 1] : [0, 1500, 4000];
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const getTeamCode = (team) => getTeamAbbr(team || '');

// ─── Fixture Calendar (Panel 1) ────────────────────────────────────────────
const FixtureCalendar = ({ fixtures, matchDetails, isMobile, squadTeams, recommendationsLoading }) => {
    if (!fixtures || fixtures.length === 0) return null;

    const buildMatchPreviewUrl = (f) => {
        const venue = encodeURIComponent(f.venue_db || f.venue || '');
        return `/venue?venue=${venue}&team1=${f.team1}&team2=${f.team2}&includeInternational=true&topTeams=20&autoload=true`;
    };

    return (
        <Box sx={{
            display: 'grid',
            gridTemplateColumns: {
                xs: '1fr',
                sm: 'repeat(2, 1fr)',
                md: `repeat(${Math.min(fixtures.length, 3)}, 1fr)`,
            },
            gap: 2,
            pb: 1,
        }}>
            {fixtures.map((f) => {
                const team1Code = getTeamCode(f.team1);
                const team2Code = getTeamCode(f.team2);
                const t1Count = (squadTeams || []).filter(t => getTeamCode(t) === team1Code).length;
                const t2Count = (squadTeams || []).filter(t => getTeamCode(t) === team2Code).length;
                const detail = (matchDetails || []).find((d) => d.match_num === f.match_num);
                const topPicks = [...(detail?.player_points || [])]
                    .sort((a, b) => (b.expected_points || 0) - (a.expected_points || 0))
                    .filter((p) => (p.expected_points || 0) > 0);
                return (
                    <Card
                        key={f.match_num}
                        component="a"
                        href={buildMatchPreviewUrl(f)}
                        sx={{
                            p: 2,
                            border: '1px solid',
                            borderColor: 'divider',
                            borderRadius: 2,
                            textDecoration: 'none',
                            color: 'inherit',
                            cursor: 'pointer',
                            transition: 'box-shadow 0.15s, border-color 0.15s',
                            '&:hover': {
                                borderColor: 'primary.main',
                                boxShadow: 2,
                            },
                        }}
                    >
                        <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                            Match {f.match_num} &middot; {f.date}
                        </Typography>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.5 }}>
                            <Chip
                                label={<CondensedName name={f.team1} type="team" />}
                                size="small"
                                sx={{
                                    bgcolor: TEAM_COLORS[team1Code] || '#666',
                                    color: ['CSK', 'LSG'].includes(team1Code) ? '#000' : '#fff',
                                    fontWeight: 700,
                                    fontSize: '0.7rem',
                                }}
                            />
                            <Typography variant="caption" sx={{ fontWeight: 600 }}>vs</Typography>
                            <Chip
                                label={<CondensedName name={f.team2} type="team" />}
                                size="small"
                                sx={{
                                    bgcolor: TEAM_COLORS[team2Code] || '#666',
                                    color: ['CSK', 'LSG'].includes(team2Code) ? '#000' : '#fff',
                                    fontWeight: 700,
                                    fontSize: '0.7rem',
                                }}
                            />
                        </Box>
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5, fontSize: '0.7rem' }}>
                            {f.venue?.split(',')[0] || ''}
                        </Typography>
                        {(t1Count > 0 || t2Count > 0) && (
                            <Typography variant="caption" sx={{ display: 'block', mt: 0.25, fontSize: '0.7rem', fontWeight: 600 }}>
                                Your players: {t1Count + t2Count}
                            </Typography>
                        )}
                        {topPicks.length > 0 && (
                            <Box sx={{ mt: 1 }}>
                                <Typography variant="caption" sx={{ display: 'block', fontWeight: 700, fontSize: '0.7rem', mb: 0.25 }}>
                                    Top Picks
                                </Typography>
                                <Box sx={{ maxHeight: 100, overflowY: 'auto' }}>
                                {topPicks.map((pick, idx) => (
                                    <Typography
                                        key={`${f.match_num}-${pick.name}`}
                                        variant="caption"
                                        color="text.secondary"
                                        sx={{ display: 'block', fontSize: '0.7rem', lineHeight: 1.4 }}
                                    >
                                        {idx + 1}. <CondensedName name={pick.name} type="player" /> (<CondensedName name={pick.team} type="team" />) &mdash; {Number(pick.expected_points || 0).toFixed(1)} pts
                                    </Typography>
                                ))}
                                </Box>
                            </Box>
                        )}
                        {topPicks.length === 0 && (
                            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.75, fontSize: '0.7rem' }}>
                                {recommendationsLoading ? 'Loading picks...' : 'No projection data'}
                            </Typography>
                        )}
                    </Card>
                );
            })}
        </Box>
    );
};

// ─── Squad Builder (Panel 2) ───────────────────────────────────────────────
const SquadBuilder = ({ squad, onRemovePlayer, onAddPlayer, onAutoPick, loading, transfersUsed, isMobile, allAvailablePlayers }) => {
    const [searchValue, setSearchValue] = useState(null);
    const roleGroups = useMemo(() => {
        const groups = { WK: [], BAT: [], AR: [], BOWL: [] };
        (squad || []).forEach((p) => {
            const role = p.role || 'BAT';
            if (groups[role]) groups[role].push(p);
            else groups.BAT.push(p);
        });
        return groups;
    }, [squad]);
    const selectablePlayers = useMemo(() => {
        const currentSquad = new Set((squad || []).map((p) => p.name));
        return (allAvailablePlayers || []).filter((p) => !currentSquad.has(p.name));
    }, [allAvailablePlayers, squad]);

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

            <Autocomplete
                size="small"
                value={searchValue}
                onChange={(_, value) => {
                    if (!value) return;
                    onAddPlayer(value);
                    setSearchValue(null);
                }}
                options={selectablePlayers}
                disabled={(squad || []).length >= 11}
                getOptionLabel={(option) => `${option.name} (${getTeamCode(option.team)}) - ${option.credits} cr`}
                isOptionEqualToValue={(option, value) => option.name === value.name}
                noOptionsText={(squad || []).length >= 11 ? 'Squad is full' : 'No players found'}
                renderInput={(params) => (
                    <TextField
                        {...params}
                        label="Add player"
                        placeholder="Type player name"
                    />
                )}
                sx={{ mb: 1.5 }}
            />

            {Object.entries(roleGroups).map(([role, players]) => (
                <Box key={role} sx={{ mb: 1.5 }}>
                    <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary', textTransform: 'uppercase' }}>
                        {role === 'WK' ? 'Wicket-keepers' : role === 'BAT' ? 'Batters' : role === 'BOWL' ? 'Bowlers' : 'All-rounders'} ({players.length})
                    </Typography>
                    {players.map((p) => {
                        const teamCode = getTeamCode(p.team);
                        return (
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
                                    <CondensedName name={p.name} type="player" />
                                </Typography>
                                <Chip
                                    label={<CondensedName name={p.team} type="team" />}
                                    size="small"
                                    sx={{
                                        height: 18,
                                        fontSize: '0.6rem',
                                        bgcolor: TEAM_COLORS[teamCode] || '#666',
                                        color: ['CSK', 'LSG'].includes(teamCode) ? '#000' : '#fff',
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
                        );
                    })}
                </Box>
            ))}

            {(!squad || squad.length === 0) && (
                <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 2 }}>
                    Use search to add your real squad, or click "Auto-pick"
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
                                Exp Pts (per match) {sortBy === 'total_expected_points' ? '▼' : ''}
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
                        {sorted.map((p) => {
                            const teamCode = getTeamCode(p.team);
                            return (
                            <TableRow key={p.name} sx={{ bgcolor: squadNames.has(p.name) ? 'action.selected' : 'inherit' }}>
                                <TableCell sx={{ fontSize: '0.8rem', fontWeight: squadNames.has(p.name) ? 700 : 400 }}>
                                    <CondensedName name={p.name} type="player" />
                                </TableCell>
                                <TableCell>
                                    <Chip
                                        label={<CondensedName name={p.team} type="team" />}
                                        size="small"
                                        sx={{
                                            height: 18,
                                            fontSize: '0.6rem',
                                            bgcolor: TEAM_COLORS[teamCode] || '#666',
                                            color: ['CSK', 'LSG'].includes(teamCode) ? '#000' : '#fff',
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
                            );
                        })}
                    </TableBody>
                </Table>
            </TableContainer>
        </Card>
    );
};

// ─── Transfer Plan View ────────────────────────────────────────────────────
const PlayerNameList = ({ names = [] }) => (
    <>
        {names.map((name, idx) => (
            <React.Fragment key={`${name}-${idx}`}>
                {idx > 0 ? ', ' : ''}
                <CondensedName name={name} type="player" />
            </React.Fragment>
        ))}
    </>
);

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
                                IN: <PlayerNameList names={gw.transfers_in} />
                            </Typography>
                        </Box>
                    )}
                    {gw.transfers_out.length > 0 && (
                        <Box>
                            <Typography variant="caption" sx={{ fontWeight: 600, color: 'error.main' }}>
                                OUT: <PlayerNameList names={gw.transfers_out} />
                            </Typography>
                        </Box>
                    )}
                    {gw.captain && (
                        <Typography variant="caption" sx={{ display: 'block', mt: 0.5 }}>
                            C: <CondensedName name={gw.captain} type="player" /> &middot; VC: <CondensedName name={gw.vice_captain} type="player" />
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
    const [recommendationsLoading, setRecommendationsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [schedule, setSchedule] = useState(null);
    const [recommendations, setRecommendations] = useState(null);
    const [allAvailablePlayers, setAllAvailablePlayers] = useState([]);
    const [squad, setSquad] = useState([]);
    const [transferPlan, setTransferPlan] = useState(null);
    const [matchesAhead, setMatchesAhead] = useState(3);
    const [tab, setTab] = useState(0);
    const [initialDataLoaded, setInitialDataLoaded] = useState(false);

    const upcomingFixtures = useMemo(() => {
        if (!schedule?.fixtures) return [];
        const today = new Date().toISOString().split('T')[0];
        return schedule.fixtures.filter(f => f.date >= today).slice(0, matchesAhead);
    }, [schedule, matchesAhead]);

    const squadTeams = useMemo(() => (squad || []).map(p => p.team), [squad]);

    const fetchRecommendations = useCallback(async ({ currentNames } = {}) => {
        const params = {
            matches_ahead: matchesAhead,
        };
        if (currentNames) {
            params.current_team = currentNames;
        }
        const res = await axios.get(`${config.API_URL}/fantasy-planner/recommendations`, { params });
        setRecommendations(res.data);
        return res.data;
    }, [matchesAhead]);

    const applyRecommendedSquad = useCallback((recommendedSquad, existingSquad = []) => {
        if (!recommendedSquad) return;
        if (!existingSquad.length) {
            setSquad(recommendedSquad);
            return;
        }
        const existingNames = new Set(existingSquad.map((p) => p.name));
        const fillerPlayers = recommendedSquad.filter((p) => !existingNames.has(p.name));
        setSquad([...existingSquad, ...fillerPlayers].slice(0, 11));
    }, []);

    const fetchRecommendationsWithRetry = useCallback(async ({ currentNames, applyToSquad = false, existingSquad = [] } = {}) => {
        setRecommendationsLoading(true);
        setError(null);
        let lastError = null;
        for (let attempt = 0; attempt < RECOMMENDATION_RETRY_DELAYS_MS.length; attempt += 1) {
            const delayMs = RECOMMENDATION_RETRY_DELAYS_MS[attempt];
            if (delayMs > 0) {
                await sleep(delayMs);
            }
            try {
                const data = await fetchRecommendations({ currentNames });
                if (applyToSquad && data?.recommended_squad) {
                    applyRecommendedSquad(data.recommended_squad, existingSquad);
                }
                return data;
            } catch (err) {
                lastError = err;
                const status = err?.response?.status;
                const retryable = !status || status === 503 || status === 504;
                const hasMoreAttempts = attempt < RECOMMENDATION_RETRY_DELAYS_MS.length - 1;
                if (!retryable || !hasMoreAttempts) {
                    break;
                }
            }
        }

        if (lastError) {
            setError(lastError.response?.data?.detail || 'Failed to fetch recommendations');
            throw lastError;
        }
        return null;
    }, [applyRecommendedSquad, fetchRecommendations]);

    const handleFetchRankings = useCallback(async () => {
        try {
            await fetchRecommendationsWithRetry();
        } catch (err) {
            // Error state already handled in retry wrapper.
        } finally {
            setRecommendationsLoading(false);
        }
    }, [fetchRecommendationsWithRetry]);

    const handleAutoPick = useCallback(async () => {
        const existingSquad = [...squad];
        const currentNames = existingSquad.map((p) => p.name).join(',') || undefined;
        setLoading(true);
        try {
            await fetchRecommendationsWithRetry({
                currentNames,
                applyToSquad: true,
                existingSquad,
            });
        } catch (err) {
            // Error state already handled in retry wrapper.
        } finally {
            setLoading(false);
            setRecommendationsLoading(false);
        }
    }, [fetchRecommendationsWithRetry, squad]);

    // Load schedule + player list on mount.
    useEffect(() => {
        let cancelled = false;
        const loadInitialData = async () => {
            try {
                const [scheduleRes, playersRes] = await Promise.all([
                    axios.get(`${config.API_URL}/fantasy-planner/schedule`),
                    axios.get(`${config.API_URL}/fantasy-planner/all-players`),
                ]);
                if (cancelled) return;
                setSchedule(scheduleRes.data);
                setAllAvailablePlayers(playersRes.data?.players || []);
                setInitialDataLoaded(true);
            } catch (err) {
                if (cancelled) return;
                setError('Failed to load fantasy planner data');
                console.error('Initial fantasy planner fetch error:', err);
            }
        };
        loadInitialData();
        return () => {
            cancelled = true;
        };
    }, []);

    // Fetch rankings/match picks after initial data is ready.
    useEffect(() => {
        if (!initialDataLoaded) return;
        handleFetchRankings();
    }, [initialDataLoaded, handleFetchRankings]);

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
        setSquad((prev) => {
            if (prev.length >= 11) return prev;
            if (prev.some((p) => p.name === player.name)) return prev;
            return [...prev, {
                name: player.name,
                team: player.team,
                role: player.role || 'BAT',
                credits: player.credits || 0,
                total_expected_points: player.total_expected_points || 0,
                match_count: player.match_count || 0,
                matches: player.matches || [],
            }];
        });
    }, []);

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
                        onChange={(e) => setMatchesAhead(Math.max(1, Math.min(5, parseInt(e.target.value, 10) || 3)))}
                        sx={{ width: 120 }}
                        inputProps={{ min: 1, max: 5 }}
                    />
                </Box>
                <FixtureCalendar
                    fixtures={upcomingFixtures}
                    matchDetails={recommendations?.match_details || []}
                    isMobile={isMobile}
                    squadTeams={squadTeams}
                    recommendationsLoading={recommendationsLoading}
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
                    onAddPlayer={handleAddPlayer}
                    onAutoPick={handleAutoPick}
                    loading={loading}
                    transfersUsed={recommendations?.transfers_needed || 0}
                    isMobile={isMobile}
                    allAvailablePlayers={allAvailablePlayers}
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
                        Captain: <strong>{recommendations.captain}</strong> (highest projected single-match points)
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
