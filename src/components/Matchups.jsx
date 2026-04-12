import React from 'react';
import axios from 'axios';
import config from '../config';
import { 
    Box, 
    Card, 
    CircularProgress,
    Alert,
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
import {
    fetchAnalyticsJson,
    getFormFlagMeta,
    normalizeAnalyticsName,
} from '../utils/analyticsApi';
import { condenseName, getFormBorderColor } from '../utils/playerNameUtils';
import { getTeamAbbr } from '../utils/teamAbbreviations';

const getPlayerFormFlag = (formFlagsByPlayer = {}, playerName = '') => (
    formFlagsByPlayer[playerName] || formFlagsByPlayer[normalizeAnalyticsName(playerName)] || null
);

const getPlayerFormMeta = (formFlagsByPlayer = {}, playerName = '') => {
    const flag = getPlayerFormFlag(formFlagsByPlayer, playerName);
    return flag ? getFormFlagMeta(flag) : null;
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




const FantasyAnalysisCard = ({ fantasyData, isMobile, formFlagsByPlayer }) => {
    if (!fantasyData || !fantasyData.top_fantasy_picks) return null;

    const getConfidenceColor = (confidence) => {
        if (confidence >= 0.8) return 'success.main';
        if (confidence >= 0.6) return 'warning.main';
        return 'error.main';
    };

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
                            <TableCell align="right" sx={{ fontWeight: 'bold', py: 1 }}>Confidence</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {fantasyData.top_fantasy_picks.map((player) => {
                            const formMeta = getPlayerFormMeta(formFlagsByPlayer, player.player_name);
                            return (
                                <TableRow key={player.player_name}>
                                <TableCell sx={{ py: 0.75, fontWeight: 'bold', borderLeft: `3px solid ${getFormBorderColor(formMeta)}` }}>
                                    {condenseName(player.player_name)}
                                </TableCell>
                                <TableCell align="right" sx={{ py: 0.75, color: 'primary.main', fontWeight: 'bold' }}>
                                    {player.expected_points?.toFixed(1) || '0.0'}
                                </TableCell>
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
                    {getTeamAbbr(decodeURIComponent(batting_team))} vs {getTeamAbbr(decodeURIComponent(bowling_team))} Matchups
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
                                                    {condenseName(bowler)}
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
                                        {condenseName(batter)}
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

const Matchups = ({ team1, team2, startDate, endDate, team1_players, team2_players, isMobile, enabled = true }) => {
    const [matchupData, setMatchupData] = React.useState(null);
    const [loading, setLoading] = React.useState(false);
    const [error, setError] = React.useState(null);
    const [formFlagsByPlayer, setFormFlagsByPlayer] = React.useState({});

    React.useEffect(() => {
        if (!enabled) return;

        const fetchMatchups = async () => {
            try {
                setMatchupData(null);
                setLoading(true);
                setError(null);
                setFormFlagsByPlayer({});

                // Build URL parameters properly
                const params = new URLSearchParams();
                params.append('start_date', startDate);
                params.append('end_date', endDate);
                
                // Add custom team players if provided
                if (team1_players && team1_players.length > 0) {
                    team1_players.forEach(player => {
                        params.append('team1_players', player);
                    });
                }
                
                if (team2_players && team2_players.length > 0) {
                    team2_players.forEach(player => {
                        params.append('team2_players', player);
                    });
                }
                
                params.append('use_current_roster', 'true');

                // Get the matchups data
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
    }, [enabled, team1, team2, startDate, endDate, team1_players, team2_players]);

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

                const formEntries = await Promise.all(formCandidates.map(async (name) => {
                    try {
                        const payload = await fetchAnalyticsJson(
                            `/player/${encodeURIComponent(name)}/rolling-form`,
                            {
                                start_date: startDate,
                                end_date: endDate,
                                role: 'all',
                                window: 10,
                            },
                        );
                        return [name, payload?.form_flag || 'neutral'];
                    } catch (fetchError) {
                        return [name, 'neutral'];
                    }
                }));

                if (cancelled) return;
                const nextFormFlags = {};
                formEntries.forEach(([name, flag]) => {
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

    if (!enabled) return null;
    if (loading) return <CircularProgress />;
    if (error) return <Alert severity="error">{error}</Alert>;
    if (!matchupData) return null;

    // Check if matchupData has the expected structure
    if (!matchupData.team1 || !matchupData.team2) {
        return <Alert severity="warning">Unexpected matchup data format.</Alert>;
    }

    // Check if there's any actual matchup data
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

    if (!hasMatchups) {
        return (
            <Alert severity="info" sx={{ mt: 3 }}>
                No matchup data found between these players in the selected time period.
            </Alert>
        );
    }

    return (
        <Box sx={{ mt: 3 }}>
            {/* Fantasy Analysis from server */}
            <FantasyAnalysisCard
                fantasyData={matchupData?.fantasy_analysis}
                isMobile={isMobile}
                formFlagsByPlayer={formFlagsByPlayer}
            />

            {/* Team 1 vs Team 2 Matchups */}
            <MatchupMatrix 
                batting_team={matchupData.team1.name}
                bowling_team={matchupData.team2.name}
                matchups={matchupData.team1.batting_matchups}
                bowlingConsolidated={matchupData.team2.bowling_consolidated}
                isMobile={isMobile}
                venue={matchupData.venue}
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
                venue={matchupData.venue}
                startDate={startDate}
                endDate={endDate}
                formFlagsByPlayer={formFlagsByPlayer}
            />
        </Box>
    );
};

export default Matchups;
