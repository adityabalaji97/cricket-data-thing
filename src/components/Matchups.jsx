import React from 'react';
import axios from 'axios';
import config from '../config';
import { 
    Box, 
    Button,
    Card, 
    Collapse,
    CircularProgress,
    Alert,
    Autocomplete,
    Chip,
    IconButton,
    Stack,
    TextField,
    ToggleButton,
    ToggleButtonGroup,
    Typography, 
    Table, 
    TableBody, 
    TableCell, 
    TableContainer, 
    TableHead, 
    TableRow,
    Tooltip,
} from '@mui/material';

import {
    Info as InfoIcon,
    Activity,
    Trophy,
} from 'lucide-react';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import {
    getFormFlagMeta,
    normalizeAnalyticsName,
    postAnalyticsJson,
} from '../utils/analyticsApi';
import { getFormBorderColor } from '../utils/playerNameUtils';
import CondensedName from './common/CondensedName';

const getPlayerFormFlag = (formFlagsByPlayer = {}, playerName = '') => (
    formFlagsByPlayer[playerName] || formFlagsByPlayer[normalizeAnalyticsName(playerName)] || null
);

const getPlayerFormMeta = (formFlagsByPlayer = {}, playerName = '') => {
    const flag = getPlayerFormFlag(formFlagsByPlayer, playerName);
    return flag ? getFormFlagMeta(flag) : null;
};

const dedupeNames = (names = []) => {
    const seen = new Set();
    const output = [];
    (names || []).forEach((name) => {
        const clean = String(name || '').trim();
        if (!clean) return;
        const key = clean.toLowerCase();
        if (seen.has(key)) return;
        seen.add(key);
        output.push(clean);
    });
    return output;
};

const toListKey = (names = []) => (
    dedupeNames(names)
        .map((name) => name.toLowerCase())
        .sort()
        .join('|')
);

const isDayNightValue = (value) => value === 'day' || value === 'night';

const resolvePostTossPlayerLinks = (
    postTossRaw = null,
    postTossPlayerDrillLinks = {},
    mode = 'general',
) => {
    const scope = mode === 'venue' ? 'venue' : 'general';
    const linksFromResponse = postTossPlayerDrillLinks?.[scope];
    if (linksFromResponse && Object.keys(linksFromResponse).length > 0) {
        return linksFromResponse;
    }
    const axisMap = postTossRaw?.players_by_axis || {};
    const links = {};
    const scores = {};
    Object.values(axisMap).forEach((axis) => {
        const players = axis?.[scope]?.players || [];
        players.forEach((row) => {
            const name = String(row?.player || '').trim();
            const link = String(row?.drill_link || '').trim();
            const score = Number(row?.xpoints || 0);
            if (!name || !link) return;
            if (!(name in links) || score >= (scores[name] ?? -Infinity)) {
                links[name] = link;
                scores[name] = score;
            }
        });
    });
    return links;
};


const MetricCell = ({ data, isMobile, bowler, isBowlingConsolidated = false }) => {
    if (!data) return <TableCell align="center">-</TableCell>;

    const getColor = (sr, balls) => {
        if (balls < 6) return 'text.secondary';
        if (isBowlingConsolidated) {
            // For bowling consolidated, lower economy is better
            if (data.economy < 6) return 'success.main';
            if (data.economy > 9) return 'error.main';
            return 'warning.main';
        } else {
            // For batting, higher strike rate is better
            if (sr >= 150) return 'success.main';
            if (sr <= 100) return 'error.main';
            return 'warning.main';
        }
    };

    let displayValue;
    let tooltipContent;

    if (isBowlingConsolidated) {
        // Normalize bowling performance to 24 balls (4 overs max)
        const normalizedRuns = (data.runs || 0) * (24 / Math.max(data.balls || 1, 1));
        const normalizedWickets = (data.wickets || 0) * (24 / Math.max(data.balls || 1, 1));
        const normalizedEconomy = normalizedRuns / 4; // 4 overs
        
        // Display format: runs-wickets (balls) @ economy (normalized to 24 balls)
        displayValue = isMobile
            ? `${Math.round(normalizedRuns)}-${normalizedWickets.toFixed(1)} (24)`
            : `${Math.round(normalizedRuns)}-${normalizedWickets.toFixed(1)} (24) @ ${normalizedEconomy.toFixed(1)}`;
            
        tooltipContent = (
            <Box>
                <Typography variant="body2">
                    <strong>Normalized to 24 balls:</strong><br />
                    Runs: {Math.round(normalizedRuns)}<br />
                    Wickets: {normalizedWickets.toFixed(1)}<br />
                    Economy: {normalizedEconomy.toFixed(2)}<br />
                    <strong>Actual:</strong><br />
                    Balls: {data.balls}<br />
                    Runs: {data.runs}<br />
                    Wickets: {data.wickets}<br />
                    Economy: {data.economy?.toFixed(2)}<br />
                    Average: {data.average?.toFixed(1) || '-'}<br />
                    Strike Rate: {data.strike_rate?.toFixed(1) || '-'}<br />
                    Dot %: {data.dot_percentage?.toFixed(1)}%<br />
                    Boundary %: {data.boundary_percentage?.toFixed(1)}%
                </Typography>
            </Box>
        );
    } else if (bowler === "Overall") {
        // Calculate effective wickets to avoid division by zero
        const effectiveWickets = data.wickets && data.wickets > 0 ? data.wickets : 1;
        // Display average (balls per wicket) @ strike rate.
        displayValue = data.average 
            ? `${data.average.toFixed(1)} (${(data.balls / effectiveWickets).toFixed(1)}) @ ${data.strike_rate.toFixed(1)}`
            : "-";
            
        tooltipContent = (
            <Box>
                <Typography variant="body2">
                    Runs: {data.runs}<br />
                    Wickets: {data.wickets}<br />
                    Balls: {data.balls}<br />
                    Average: {data.average ? data.average.toFixed(1) : '-'}<br />
                    Strike Rate: {data.strike_rate.toFixed(1)}<br />
                    Boundary %: {data.boundary_percentage?.toFixed(1)}%<br />
                    Dot %: {data.dot_percentage?.toFixed(1)}%
                </Typography>
            </Box>
        );
    } else {
        displayValue = isMobile
            ? `${data.runs}-${data.wickets} (${data.balls})`
            : `${data.runs}-${data.wickets} (${data.balls}) @ ${data.strike_rate.toFixed(1)}`;
            
        tooltipContent = (
            <Box>
                <Typography variant="body2">
                    Runs: {data.runs}<br />
                    Wickets: {data.wickets}<br />
                    Balls: {data.balls}<br />
                    Average: {data.average ? data.average.toFixed(1) : '-'}<br />
                    Strike Rate: {data.strike_rate.toFixed(1)}<br />
                    Boundary %: {data.boundary_percentage?.toFixed(1)}%<br />
                    Dot %: {data.dot_percentage?.toFixed(1)}%
                </Typography>
            </Box>
        );
    }

    return (
        <TableCell 
            align="center" 
            sx={{ 
                color: getColor(data.strike_rate, data.balls),
                fontSize: isMobile ? '0.75rem' : '0.875rem',
                padding: isMobile ? '4px' : '8px',
                backgroundColor: isBowlingConsolidated ? 'rgba(25, 118, 210, 0.08)' : 'inherit'
            }}
        >
            <Tooltip title={tooltipContent}>
                <Box>{displayValue}</Box>
            </Tooltip>
        </TableCell>
    );
};




const FantasyAnalysisCard = ({
    fantasyData,
    isMobile,
    formFlagsByPlayer,
    postTossXpoints = {},
    postTossDelta = {},
    postTossPlayerLinks = {},
}) => {
    if (!fantasyData || !fantasyData.top_fantasy_picks) return null;

    const getConfidenceColor = (confidence) => {
        if (confidence >= 0.8) return 'success.main';
        if (confidence >= 0.6) return 'warning.main';
        return 'error.main';
    };

    const hasPostToss = Object.keys(postTossXpoints || {}).length > 0;
    const sortedPicks = [...(fantasyData?.top_fantasy_picks || [])];
    if (hasPostToss) {
        sortedPicks.sort((a, b) => {
            const aPost = Number(postTossXpoints?.[a.player_name]);
            const bPost = Number(postTossXpoints?.[b.player_name]);
            const aHas = Number.isFinite(aPost);
            const bHas = Number.isFinite(bPost);
            if (aHas && bHas && bPost !== aPost) return bPost - aPost;
            if (aHas !== bHas) return aHas ? -1 : 1;
            return Number(b.expected_points || 0) - Number(a.expected_points || 0);
        });
    }

    return (
        <Card sx={{
            p: 2,
            mb: 3,
            backgroundColor: isMobile ? 'transparent' : undefined,
            boxShadow: isMobile ? 0 : undefined
        }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1, gap: 1 }}>
                <Trophy size={20} />
                <Typography variant={isMobile ? "subtitle1" : "h6"}>
                    Fantasy Analysis - Top Picks
                </Typography>
            </Box>
            <TableContainer sx={{ maxHeight: 220, overflowY: 'auto' }}>
                <Table size="small" stickyHeader>
                    <TableHead>
                        <TableRow>
                            <TableCell sx={{ fontWeight: 'bold', py: 1 }}>Player</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold', py: 1 }}>xPoints</TableCell>
                            {hasPostToss && (
                                <TableCell align="right" sx={{ fontWeight: 'bold', py: 1 }}>xPoints (post-toss)</TableCell>
                            )}
                            {hasPostToss && (
                                <TableCell align="right" sx={{ fontWeight: 'bold', py: 1 }}>Δ</TableCell>
                            )}
                            <TableCell align="right" sx={{ fontWeight: 'bold', py: 1 }}>Confidence</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {sortedPicks.map((player) => {
                            const formMeta = getPlayerFormMeta(formFlagsByPlayer, player.player_name);
                            const postToss = postTossXpoints?.[player.player_name];
                            const delta = postTossDelta?.[player.player_name];
                            const drillLink = postTossPlayerLinks?.[player.player_name]
                                || postTossPlayerLinks?.[normalizeAnalyticsName(player.player_name)];
                            return (
                                <TableRow key={player.player_name}>
                                <TableCell sx={{ py: 0.75, fontWeight: 'bold', borderLeft: `3px solid ${getFormBorderColor(formMeta)}` }}>
                                    <CondensedName name={player.player_name} type="player" />
                                </TableCell>
                                <TableCell align="right" sx={{ py: 0.75, color: 'primary.main', fontWeight: 'bold' }}>
                                    {player.expected_points?.toFixed(1) || '0.0'}
                                </TableCell>
                                {hasPostToss && (
                                    <TableCell align="right" sx={{ py: 0.75, color: 'secondary.main', fontWeight: 600 }}>
                                        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 0.25 }}>
                                            <Box component="span">
                                                {typeof postToss === 'number' ? postToss.toFixed(1) : '—'}
                                            </Box>
                                            {drillLink && (
                                                <Tooltip title="Open player query drill-down">
                                                    <IconButton
                                                        component="a"
                                                        href={drillLink}
                                                        target="_blank"
                                                        rel="noreferrer"
                                                        size="small"
                                                        sx={{ p: 0.25 }}
                                                    >
                                                        <OpenInNewIcon sx={{ fontSize: 14 }} />
                                                    </IconButton>
                                                </Tooltip>
                                            )}
                                        </Box>
                                    </TableCell>
                                )}
                                {hasPostToss && (
                                    <TableCell
                                        align="right"
                                        sx={{
                                            py: 0.75,
                                            color: typeof delta === 'number'
                                                ? (delta > 0 ? 'success.main' : (delta < 0 ? 'error.main' : 'text.secondary'))
                                                : 'text.secondary',
                                        }}
                                    >
                                        {typeof delta === 'number' ? `${delta > 0 ? '+' : ''}${delta.toFixed(1)}` : '—'}
                                    </TableCell>
                                )}
                                <TableCell align="right" sx={{ py: 0.75, color: getConfidenceColor(player.confidence || 0) }}>
                                    {((player.confidence || 0) * 100).toFixed(0)}%
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

const MatchupMatrix = ({ 
    batting_team, 
    bowling_team, 
    matchups, 
    bowlingConsolidated, 
    isMobile, 
    venue, 
    startDate, 
    endDate,
    formFlagsByPlayer = {},
}) => {
    const batters = Object.keys(matchups);
    const bowlers = React.useMemo(() => {
        const cols = Array.from(
            new Set(
                batters.flatMap(batter =>
                    Object.keys(matchups[batter] || {})
                )
            )
        );
        // Remove "Overall" if present, then append it at the end
        const overallIndex = cols.indexOf("Overall");
        if (overallIndex !== -1) {
            cols.splice(overallIndex, 1);
        }
        cols.push("Overall");
        return cols;
    }, [batters, matchups]);

    const handleBatterClick = (batter) => {
        const params = new URLSearchParams();
        params.append('name', batter);
        if (venue && venue !== "All Venues") {
            params.append('venue', venue);
        }
        if (startDate) {
            params.append('start_date', startDate);
        }
        if (endDate) {
            params.append('end_date', endDate);
        }
        params.append('autoload', 'true');
        window.open(`${window.location.origin}/player?${params.toString()}`, '_blank');
    };

    return (
        <Card sx={{
            p: 2,
            mb: 3,
            backgroundColor: isMobile ? 'transparent' : undefined,
            boxShadow: isMobile ? 0 : undefined
        }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 1 }}>
                <Typography variant={isMobile ? "subtitle1" : "h6"}>
                    <CondensedName name={decodeURIComponent(batting_team)} type="team" /> vs <CondensedName name={decodeURIComponent(bowling_team)} type="team" /> Matchups
                </Typography>
                <Tooltip title="Runs-Wickets (Balls) @ Strike Rate | Hover for more stats">
                    <InfoIcon size={16} />
                </Tooltip>
            </Box>
            <TableContainer>
                <Table size={isMobile ? "small" : "medium"}>
                    <TableHead>
                        <TableRow>
                            <TableCell 
                                sx={{ 
                                    fontWeight: 'bold',
                                    whiteSpace: 'nowrap',
                                    position: 'sticky',
                                    left: 0,
                                    backgroundColor: 'background.paper',
                                    zIndex: 1
                                }}
                            >
                                Batter
                            </TableCell>
                            {bowlers.map((bowler) => {
                                const formMeta = getPlayerFormMeta(formFlagsByPlayer, bowler);
                                const params = new URLSearchParams({
                                    name: bowler,
                                    tab: 'bowling',
                                    ...(venue && venue !== "All Venues" ? { venue } : {}),
                                    ...(startDate ? { start_date: startDate } : {}),
                                    ...(endDate ? { end_date: endDate } : {}),
                                    autoload: 'true'
                                });
                                return (
                                    <TableCell
                                        key={bowler}
                                        align="center"
                                        sx={{
                                            fontWeight: 'bold',
                                            whiteSpace: 'nowrap',
                                            minWidth: isMobile ? '80px' : '120px',
                                            cursor: bowler === "Overall" ? 'default' : 'pointer'
                                        }}
                                    >
                                        {bowler === "Overall" ? (
                                            <span style={{
                                                textDecoration: 'none',
                                                color: 'inherit',
                                                display: 'block',
                                                width: '100%',
                                                height: '100%'
                                            }}>
                                                Consolidated
                                            </span>
                                        ) : (
                                            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', borderBottom: `3px solid ${getFormBorderColor(formMeta)}` }}>
                                                <a
                                                    href={`${window.location.origin}/player?${params.toString()}`}
                                                    target="_blank"
                                                    rel="noreferrer"
                                                    style={{
                                                        textDecoration: 'none',
                                                        color: 'inherit',
                                                        display: 'block',
                                                        width: '100%',
                                                        height: '100%'
                                                    }}
                                                >
                                                    <CondensedName name={bowler} type="player" />
                                                </a>
                                            </Box>
                                        )}
                                    </TableCell>
                                );
                            })}
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {/* Batting matchup rows */}
                        {batters.map((batter) => {
                            const formMeta = getPlayerFormMeta(formFlagsByPlayer, batter);
                            return (
                            <TableRow key={batter} onClick={() => handleBatterClick(batter)} style={{ cursor: 'pointer' }}>
                                <TableCell
                                    component="th"
                                    scope="row"
                                    sx={{
                                        fontWeight: 'bold',
                                        whiteSpace: 'nowrap',
                                        position: 'sticky',
                                        left: 0,
                                        backgroundColor: 'background.paper',
                                        zIndex: 1,
                                        cursor: 'pointer',
                                        boxShadow: `inset 3px 0 0 0 ${getFormBorderColor(formMeta)}`
                                    }}
                                    onClick={() => handleBatterClick(batter)}
                                >
                                    <a
                                        href={`${window.location.origin}/player?${new URLSearchParams({
                                            name: batter,
                                            ...(venue && venue !== "All Venues" ? { venue } : {}),
                                            ...(startDate ? { start_date: startDate } : {}),
                                            ...(endDate ? { end_date: endDate } : {}),
                                            autoload: 'true'
                                        }).toString()}`}
                                        target="_blank"
                                        rel="noreferrer"
                                        style={{
                                            textDecoration: 'none',
                                            color: 'inherit',
                                            display: 'block',
                                            width: '100%',
                                            height: '100%'
                                        }}
                                    >
                                        <CondensedName name={batter} type="player" />
                                    </a>
                                </TableCell>
                                {bowlers.map(bowler => (
                                    <MetricCell 
                                        key={`${batter}-${bowler}`}
                                        data={matchups[batter]?.[bowler]}
                                        isMobile={isMobile}
                                        bowler={bowler}
                                    />
                                ))}
                            </TableRow>
                            );
                        })}
                        
                        {/* Bowling consolidated row */}
                        {bowlingConsolidated && Object.keys(bowlingConsolidated).length > 0 && (
                            <TableRow sx={{ backgroundColor: 'rgba(25, 118, 210, 0.04)' }}>
                                <TableCell 
                                    component="th" 
                                    scope="row"
                                    sx={{ 
                                        fontWeight: 'bold',
                                        whiteSpace: 'nowrap',
                                        position: 'sticky',
                                        left: 0,
                                        backgroundColor: 'rgba(25, 118, 210, 0.08)',
                                        zIndex: 1
                                    }}
                                >
                                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                        <Activity size={16} />
                                    </Box>
                                </TableCell>
                                {bowlers.map(bowler => {
                                    if (bowler === "Overall") {
                                        return <TableCell key={bowler} align="center" sx={{ backgroundColor: 'rgba(25, 118, 210, 0.08)' }}>-</TableCell>;
                                    }
                                    
                                    // Better lookup logic for the consolidated row
                                    const bowlerData = bowlingConsolidated[bowler];
                                    
                                    return (
                                        <MetricCell 
                                            key={`bowling-consolidated-${bowler}`}
                                            data={bowlerData}
                                            isMobile={isMobile}
                                            bowler={bowler}
                                            isBowlingConsolidated={true}
                                        />
                                    );
                                })}
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </TableContainer>
        </Card>
    );
};

const Matchups = ({
    team1,
    team2,
    venue = 'All Venues',
    startDate,
    endDate,
    team1_players,
    team2_players,
    isMobile,
    enabled = true,
    dayNightFilter = 'all',
    postTossXpoints = {},
    postTossDelta = {},
    postTossRaw = null,
    postTossPlayerDrillLinks = {},
}) => {
    const [matchupData, setMatchupData] = React.useState(null);
    const [loading, setLoading] = React.useState(false);
    const [error, setError] = React.useState(null);
    const [formFlagsByPlayer, setFormFlagsByPlayer] = React.useState({});
    const [axisEditorOpen, setAxisEditorOpen] = React.useState(false);
    const [team1AxisDraftPlayers, setTeam1AxisDraftPlayers] = React.useState(dedupeNames(team1_players || []));
    const [team2AxisDraftPlayers, setTeam2AxisDraftPlayers] = React.useState(dedupeNames(team2_players || []));
    const [team1AxisAppliedPlayers, setTeam1AxisAppliedPlayers] = React.useState(dedupeNames(team1_players || []));
    const [team2AxisAppliedPlayers, setTeam2AxisAppliedPlayers] = React.useState(dedupeNames(team2_players || []));
    const [team1RosterOptions, setTeam1RosterOptions] = React.useState([]);
    const [team2RosterOptions, setTeam2RosterOptions] = React.useState([]);
    const [postTossMode, setPostTossMode] = React.useState('off'); // off | general | venue
    const [postTossMatrixLoading, setPostTossMatrixLoading] = React.useState(false);
    const [postTossMatrixError, setPostTossMatrixError] = React.useState(null);
    const [postTossMatrixData, setPostTossMatrixData] = React.useState({
        firstInnings: null,
        secondInnings: null,
    });

    const incomingTeam1PlayersRef = React.useRef(dedupeNames(team1_players || []));
    const incomingTeam2PlayersRef = React.useRef(dedupeNames(team2_players || []));
    const incomingTeam1Key = React.useMemo(() => toListKey(team1_players || []), [team1_players]);
    const incomingTeam2Key = React.useMemo(() => toListKey(team2_players || []), [team2_players]);
    const incomingPlayersKey = `${incomingTeam1Key}::${incomingTeam2Key}`;
    const hasPostTossContext = Boolean(
        postTossRaw?.batting_first_team
        && postTossRaw?.team1_id
        && postTossRaw?.team2_id
    );
    const postTossLinksScope = postTossMode === 'venue' ? 'venue' : 'general';
    const postTossPlayerLinks = React.useMemo(
        () => resolvePostTossPlayerLinks(postTossRaw, postTossPlayerDrillLinks, postTossLinksScope),
        [postTossRaw, postTossPlayerDrillLinks, postTossLinksScope],
    );
    const matrixAxesLocked = hasPostTossContext && postTossMode !== 'off';

    React.useEffect(() => {
        if (!hasPostTossContext && postTossMode !== 'off') {
            setPostTossMode('off');
        }
    }, [hasPostTossContext, postTossMode]);

    React.useEffect(() => {
        incomingTeam1PlayersRef.current = dedupeNames(team1_players || []);
        incomingTeam2PlayersRef.current = dedupeNames(team2_players || []);
    }, [team1_players, team2_players]);

    React.useEffect(() => {
        const incomingTeam1Players = incomingTeam1PlayersRef.current;
        const incomingTeam2Players = incomingTeam2PlayersRef.current;
        if (incomingTeam1Players.length || incomingTeam2Players.length) {
            setTeam1AxisDraftPlayers(incomingTeam1Players);
            setTeam2AxisDraftPlayers(incomingTeam2Players);
            setTeam1AxisAppliedPlayers(incomingTeam1Players);
            setTeam2AxisAppliedPlayers(incomingTeam2Players);
        }
    }, [incomingPlayersKey]);

    React.useEffect(() => {
        if (incomingTeam1Key || incomingTeam2Key) return;
        setTeam1AxisDraftPlayers([]);
        setTeam2AxisDraftPlayers([]);
        setTeam1AxisAppliedPlayers([]);
        setTeam2AxisAppliedPlayers([]);
        setAxisEditorOpen(false);
    }, [team1, team2, incomingTeam1Key, incomingTeam2Key]);

    React.useEffect(() => {
        let cancelled = false;
        const loadRosterOptions = async () => {
            try {
                const rosterParams = isDayNightValue(dayNightFilter)
                    ? { day_or_night: dayNightFilter }
                    : {};
                const [team1Res, team2Res] = await Promise.all([
                    axios.get(`${config.API_URL}/teams/${encodeURIComponent(team1)}/roster`, { params: rosterParams }),
                    axios.get(`${config.API_URL}/teams/${encodeURIComponent(team2)}/roster`, { params: rosterParams }),
                ]);
                if (cancelled) return;
                const t1 = dedupeNames((team1Res.data?.players || []).map((row) => row?.name));
                const t2 = dedupeNames((team2Res.data?.players || []).map((row) => row?.name));
                setTeam1RosterOptions(t1);
                setTeam2RosterOptions(t2);
            } catch (rosterError) {
                if (cancelled) return;
                console.error('Error loading roster options for matchup axes:', rosterError);
                setTeam1RosterOptions([]);
                setTeam2RosterOptions([]);
            }
        };
        if (enabled && team1 && team2) {
            loadRosterOptions();
        }
        return () => {
            cancelled = true;
        };
    }, [enabled, team1, team2, dayNightFilter]);

    React.useEffect(() => {
        if (!enabled) return;
        const fetchMatchups = async () => {
            try {
                setMatchupData(null);
                setLoading(true);
                setError(null);
                setFormFlagsByPlayer({});

                const params = new URLSearchParams();
                if (startDate) params.append('start_date', startDate);
                if (endDate) params.append('end_date', endDate);

                const effectiveTeam1Players = dedupeNames(team1AxisAppliedPlayers || []);
                const effectiveTeam2Players = dedupeNames(team2AxisAppliedPlayers || []);
                const hasCustomPlayers = Boolean(
                    effectiveTeam1Players.length > 0 && effectiveTeam2Players.length > 0
                );

                if (hasCustomPlayers) {
                    effectiveTeam1Players.forEach(player => {
                        params.append('team1_players', player);
                    });
                    effectiveTeam2Players.forEach(player => {
                        params.append('team2_players', player);
                    });
                }

                params.append('use_current_roster', hasCustomPlayers ? 'false' : 'true');
                if (isDayNightValue(dayNightFilter)) {
                    params.append('day_or_night', dayNightFilter);
                }

                const matchupsResponse = await axios.get(`${config.API_URL}/teams/${encodeURIComponent(team1)}/${encodeURIComponent(team2)}/matchups?${params.toString()}`);

                setMatchupData(matchupsResponse.data);
            } catch (error) {
                console.error('Error fetching matchups:', error);
                setError(error.response?.data?.detail || 'Error fetching matchups');
            } finally {
                setLoading(false);
            }
        };

        fetchMatchups();
    }, [enabled, team1, team2, startDate, endDate, dayNightFilter, team1AxisAppliedPlayers, team2AxisAppliedPlayers]);

    React.useEffect(() => {
        if (!enabled) return;
        if (!hasPostTossContext || postTossMode === 'off') {
            setPostTossMatrixError(null);
            setPostTossMatrixData({ firstInnings: null, secondInnings: null });
            return;
        }

        let cancelled = false;
        const fetchPostTossMatrix = async () => {
            setPostTossMatrixLoading(true);
            setPostTossMatrixError(null);
            try {
                const battingFirst = postTossRaw?.batting_first_team;
                const battingSecond = postTossRaw?.batting_second_team
                    || (battingFirst === postTossRaw?.team1_id ? postTossRaw?.team2_id : postTossRaw?.team1_id);
                const team1Xi = dedupeNames(postTossRaw?.team1_xi || []);
                const team2Xi = dedupeNames(postTossRaw?.team2_xi || []);
                const xiByTeam = {
                    [postTossRaw?.team1_id]: team1Xi,
                    [postTossRaw?.team2_id]: team2Xi,
                };
                const firstXi = dedupeNames(xiByTeam?.[battingFirst] || []);
                const secondXi = dedupeNames(xiByTeam?.[battingSecond] || []);

                if (!battingFirst || !battingSecond || firstXi.length === 0 || secondXi.length === 0) {
                    throw new Error('Missing post-toss teams or XI to build innings matchups');
                }

                const windowScope = postTossMode === 'venue' ? 'venue' : 'general';
                const windowStartDate = postTossRaw?.windows?.[windowScope]?.start_date || startDate;
                const windowEndDate = postTossRaw?.windows?.[windowScope]?.end_date || endDate;

                const commonParams = (inningsValue, battingXi, bowlingXi) => {
                    const params = new URLSearchParams();
                    if (windowStartDate) params.append('start_date', windowStartDate);
                    if (windowEndDate) params.append('end_date', windowEndDate);
                    battingXi.forEach((player) => params.append('team1_players', player));
                    bowlingXi.forEach((player) => params.append('team2_players', player));
                    params.append('use_current_roster', 'false');
                    params.append('innings_position', String(inningsValue));
                    params.append('min_balls', '1');
                    if (postTossMode === 'venue' && venue && venue !== 'All Venues') {
                        params.append('venue_filter', venue);
                    }
                    if (isDayNightValue(dayNightFilter)) {
                        params.append('day_or_night', dayNightFilter);
                    }
                    return params.toString();
                };

                const [firstRes, secondRes] = await Promise.all([
                    axios.get(
                        `${config.API_URL}/teams/${encodeURIComponent(battingFirst)}/${encodeURIComponent(battingSecond)}/matchups?${commonParams(1, firstXi, secondXi)}`,
                    ),
                    axios.get(
                        `${config.API_URL}/teams/${encodeURIComponent(battingSecond)}/${encodeURIComponent(battingFirst)}/matchups?${commonParams(2, secondXi, firstXi)}`,
                    ),
                ]);

                if (cancelled) return;
                setPostTossMatrixData({
                    firstInnings: firstRes.data || null,
                    secondInnings: secondRes.data || null,
                });
            } catch (fetchError) {
                if (cancelled) return;
                console.error('Error fetching post-toss matchup matrices:', fetchError);
                setPostTossMatrixError(fetchError?.response?.data?.detail || fetchError?.message || 'Failed to load post-toss matchups');
                setPostTossMatrixData({ firstInnings: null, secondInnings: null });
            } finally {
                if (!cancelled) setPostTossMatrixLoading(false);
            }
        };

        fetchPostTossMatrix();
        return () => {
            cancelled = true;
        };
    }, [enabled, hasPostTossContext, postTossMode, postTossRaw, startDate, endDate, venue, dayNightFilter]);

    React.useEffect(() => {
        if (!enabled || !matchupData?.team1 || !matchupData?.team2) return;

        let cancelled = false;

        const loadAnalytics = async () => {
            try {
                const fantasyNames = (matchupData?.fantasy_analysis?.top_fantasy_picks || []).map((row) => row.player_name);
                const matrixBatters = [
                    ...Object.keys(matchupData?.team1?.batting_matchups || {}),
                    ...Object.keys(matchupData?.team2?.batting_matchups || {}),
                ];
                const matrixBowlers = [
                    ...Object.keys(matchupData?.team1?.bowling_consolidated || {}),
                    ...Object.keys(matchupData?.team2?.bowling_consolidated || {}),
                ];
                const formCandidates = Array.from(new Set(
                    [...fantasyNames, ...matrixBatters, ...matrixBowlers].filter(Boolean),
                )).slice(0, 80);

                const result = await postAnalyticsJson('/players/form-flags', {
                    player_names: formCandidates,
                    window: 10,
                });

                if (cancelled) return;
                const serverFlags = result?.flags || {};
                const nextFormFlags = {};
                Object.entries(serverFlags).forEach(([name, flag]) => {
                    nextFormFlags[name] = flag;
                    const normalized = normalizeAnalyticsName(name);
                    if (normalized) {
                        nextFormFlags[normalized] = flag;
                    }
                });
                setFormFlagsByPlayer(nextFormFlags);
            } catch (fetchError) {
                if (cancelled) return;
                console.error('Error fetching matchup analytics overlays:', fetchError);
            }
        };

        loadAnalytics();
        return () => {
            cancelled = true;
        };
    }, [enabled, matchupData, startDate, endDate]);

    React.useEffect(() => {
        if (!enabled || !matchupData?.team1 || !matchupData?.team2) return;
        const hasIncomingCustom = Boolean(
            incomingTeam1Key
            || incomingTeam2Key
        );
        if (hasIncomingCustom) return;
        if (team1AxisDraftPlayers.length === 0 && Array.isArray(matchupData?.team1?.players)) {
            setTeam1AxisDraftPlayers(dedupeNames(matchupData.team1.players));
        }
        if (team2AxisDraftPlayers.length === 0 && Array.isArray(matchupData?.team2?.players)) {
            setTeam2AxisDraftPlayers(dedupeNames(matchupData.team2.players));
        }
    }, [
        enabled,
        matchupData,
        incomingTeam1Key,
        incomingTeam2Key,
        team1AxisDraftPlayers.length,
        team2AxisDraftPlayers.length,
    ]);

    if (!enabled) return null;
    if (loading) return <CircularProgress />;
    if (error) return <Alert severity="error">{error}</Alert>;
    if (!matchupData) return null;

    // Check if matchupData has the expected structure
    if (!matchupData.team1 || !matchupData.team2) {
        return <Alert severity="warning">Unexpected matchup data format.</Alert>;
    }

    // Check if there's any actual matchup data in the default view.
    const hasMatchups = (
        (
            matchupData.team1.batting_matchups
            && Object.keys(matchupData.team1.batting_matchups).length > 0
        )
        || (
            matchupData.team2.batting_matchups
            && Object.keys(matchupData.team2.batting_matchups).length > 0
        )
    );

    if (!hasMatchups && postTossMode === 'off') {
        return (
            <Alert severity="info" sx={{ mt: 3 }}>
                No matchup data found between these players in the selected time period.
            </Alert>
        );
    }

    const team1Options = dedupeNames([
        ...team1RosterOptions,
        ...(matchupData?.team1?.players || []),
        ...team1AxisDraftPlayers,
    ]);
    const team2Options = dedupeNames([
        ...team2RosterOptions,
        ...(matchupData?.team2?.players || []),
        ...team2AxisDraftPlayers,
    ]);
    const canApplyAxes = team1AxisDraftPlayers.length > 0 && team2AxisDraftPlayers.length > 0;
    const hasDraftChanges = (
        toListKey(team1AxisDraftPlayers) !== toListKey(team1AxisAppliedPlayers)
        || toListKey(team2AxisDraftPlayers) !== toListKey(team2AxisAppliedPlayers)
    );

    return (
        <Box sx={{ mt: 3 }}>
            {hasPostTossContext && (
                <Card
                    sx={{
                        p: 2,
                        mb: 2,
                        backgroundColor: isMobile ? 'transparent' : undefined,
                        boxShadow: isMobile ? 0 : undefined,
                    }}
                >
                    <Stack
                        direction={isMobile ? 'column' : 'row'}
                        spacing={1}
                        alignItems={isMobile ? 'flex-start' : 'center'}
                        justifyContent="space-between"
                    >
                        <Typography variant={isMobile ? "subtitle1" : "h6"}>
                            Post-Toss Matchup View
                        </Typography>
                        <ToggleButtonGroup
                            size="small"
                            value={postTossMode}
                            exclusive
                            onChange={(event, nextValue) => {
                                if (!nextValue) return;
                                setPostTossMode(nextValue);
                            }}
                        >
                            <ToggleButton value="off">Off</ToggleButton>
                            <ToggleButton value="general">General</ToggleButton>
                            <ToggleButton value="venue">At Venue</ToggleButton>
                        </ToggleButtonGroup>
                    </Stack>
                </Card>
            )}

            {!matrixAxesLocked && (
            <Card
                sx={{
                    p: 2,
                    mb: 2,
                    backgroundColor: isMobile ? 'transparent' : undefined,
                    boxShadow: isMobile ? 0 : undefined,
                }}
            >
                <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }}>
                    <Typography variant={isMobile ? "subtitle1" : "h6"}>
                        Matchup Matrix Axes
                    </Typography>
                    <Button
                        size="small"
                        variant={axisEditorOpen ? "contained" : "outlined"}
                        onClick={() => setAxisEditorOpen((prev) => !prev)}
                    >
                        {axisEditorOpen ? "Hide Axes" : "Edit Axes"}
                    </Button>
                </Stack>
                <Collapse in={axisEditorOpen}>
                    <Stack direction="column" spacing={1.5}>
                        <Autocomplete
                            multiple
                            options={team1Options}
                            value={team1AxisDraftPlayers}
                            onChange={(event, value) => setTeam1AxisDraftPlayers(dedupeNames(value))}
                            renderTags={(value, getTagProps) =>
                                value.map((option, index) => (
                                    <Chip variant="outlined" label={option} {...getTagProps({ index })} key={`${option}-${index}`} />
                                ))
                            }
                            renderInput={(params) => (
                                <TextField
                                    {...params}
                                    size="small"
                                    label={`${matchupData.team1.name} batters/bowlers`}
                                    helperText="Edit players, then click Update matchups."
                                />
                            )}
                        />
                        <Autocomplete
                            multiple
                            options={team2Options}
                            value={team2AxisDraftPlayers}
                            onChange={(event, value) => setTeam2AxisDraftPlayers(dedupeNames(value))}
                            renderTags={(value, getTagProps) =>
                                value.map((option, index) => (
                                    <Chip variant="outlined" label={option} {...getTagProps({ index })} key={`${option}-${index}`} />
                                ))
                            }
                            renderInput={(params) => (
                                <TextField
                                    {...params}
                                    size="small"
                                    label={`${matchupData.team2.name} batters/bowlers`}
                                    helperText="Changes are local until you update."
                                />
                            )}
                        />
                        <Stack direction={isMobile ? "column" : "row"} spacing={1}>
                            <Button
                                variant="contained"
                                onClick={() => {
                                    setTeam1AxisAppliedPlayers(dedupeNames(team1AxisDraftPlayers));
                                    setTeam2AxisAppliedPlayers(dedupeNames(team2AxisDraftPlayers));
                                }}
                                disabled={!canApplyAxes || !hasDraftChanges || loading}
                            >
                                Update Matchups
                            </Button>
                            <Button
                                variant="outlined"
                                onClick={() => {
                                    setTeam1AxisDraftPlayers(dedupeNames(team1AxisAppliedPlayers));
                                    setTeam2AxisDraftPlayers(dedupeNames(team2AxisAppliedPlayers));
                                }}
                                disabled={!hasDraftChanges || loading}
                            >
                                Reset Changes
                            </Button>
                        </Stack>
                    </Stack>
                </Collapse>
            </Card>
            )}
            {matrixAxesLocked && (
                <Alert severity="info" sx={{ mb: 2 }}>
                    Playing XI axes are locked to the post-toss teams while post-toss mode is active.
                </Alert>
            )}

            {/* Fantasy Analysis from server */}
            <FantasyAnalysisCard
                fantasyData={matchupData?.fantasy_analysis}
                isMobile={isMobile}
                formFlagsByPlayer={formFlagsByPlayer}
                postTossXpoints={postTossXpoints}
                postTossDelta={postTossDelta}
                postTossPlayerLinks={postTossPlayerLinks}
            />

            {postTossMode === 'off' && (
                <>
                    {/* Team 1 vs Team 2 Matchups */}
                    <MatchupMatrix
                        batting_team={matchupData.team1.name}
                        bowling_team={matchupData.team2.name}
                        matchups={matchupData.team1.batting_matchups}
                        bowlingConsolidated={matchupData.team2.bowling_consolidated}
                        isMobile={isMobile}
                        venue={venue}
                        startDate={startDate}
                        endDate={endDate}
                        formFlagsByPlayer={formFlagsByPlayer}
                    />

                    {/* Team 2 vs Team 1 Matchups */}
                    <MatchupMatrix
                        batting_team={matchupData.team2.name}
                        bowling_team={matchupData.team1.name}
                        matchups={matchupData.team2.batting_matchups}
                        bowlingConsolidated={matchupData.team1.bowling_consolidated}
                        isMobile={isMobile}
                        venue={venue}
                        startDate={startDate}
                        endDate={endDate}
                        formFlagsByPlayer={formFlagsByPlayer}
                    />
                </>
            )}

            {postTossMode !== 'off' && (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                    {postTossMatrixLoading && <CircularProgress size={24} />}
                    {postTossMatrixError && <Alert severity="warning">{postTossMatrixError}</Alert>}

                    {!postTossMatrixLoading && !postTossMatrixError && (
                        <>
                            <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                                1st Innings Matchups
                            </Typography>
                            {postTossMatrixData?.firstInnings?.team1?.batting_matchups
                                && Object.keys(postTossMatrixData.firstInnings.team1.batting_matchups).length > 0 ? (
                                <MatchupMatrix
                                    batting_team={postTossMatrixData.firstInnings.team1.name}
                                    bowling_team={postTossMatrixData.firstInnings.team2.name}
                                    matchups={postTossMatrixData.firstInnings.team1.batting_matchups}
                                    bowlingConsolidated={postTossMatrixData.firstInnings.team2.bowling_consolidated}
                                    isMobile={isMobile}
                                    venue={postTossMode === 'venue' ? venue : 'All Venues'}
                                    startDate={startDate}
                                    endDate={endDate}
                                    formFlagsByPlayer={formFlagsByPlayer}
                                />
                            ) : (
                                <Alert severity="info">No 1st-innings matchup data for the selected post-toss filters.</Alert>
                            )}

                            <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                                2nd Innings Matchups
                            </Typography>
                            {postTossMatrixData?.secondInnings?.team1?.batting_matchups
                                && Object.keys(postTossMatrixData.secondInnings.team1.batting_matchups).length > 0 ? (
                                <MatchupMatrix
                                    batting_team={postTossMatrixData.secondInnings.team1.name}
                                    bowling_team={postTossMatrixData.secondInnings.team2.name}
                                    matchups={postTossMatrixData.secondInnings.team1.batting_matchups}
                                    bowlingConsolidated={postTossMatrixData.secondInnings.team2.bowling_consolidated}
                                    isMobile={isMobile}
                                    venue={postTossMode === 'venue' ? venue : 'All Venues'}
                                    startDate={startDate}
                                    endDate={endDate}
                                    formFlagsByPlayer={formFlagsByPlayer}
                                />
                            ) : (
                                <Alert severity="info">No 2nd-innings matchup data for the selected post-toss filters.</Alert>
                            )}
                        </>
                    )}
                </Box>
            )}
        </Box>
    );
};

export default Matchups;
