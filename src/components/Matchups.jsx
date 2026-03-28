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
    Chip,
    Grid,
    Paper,
    LinearProgress,
    Divider,
    Badge
} from '@mui/material';

import {
    Info as InfoIcon,
    Activity,
    Trophy,
    Star
} from 'lucide-react';


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
        const normalizedBalls = Math.min(data.balls || 0, 24);
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




const FantasyAnalysisCard = ({ fantasyData, isMobile }) => {
    if (!fantasyData || !fantasyData.top_fantasy_picks) return null;
    const getRoleColor = (role) => {
        switch (role?.toLowerCase()) {
            case 'batting': return 'success';
            case 'bowling': return 'primary';
            case 'all-round': return 'secondary';
            case 'wicket-keeper': return 'warning';
            default: return 'default';
        }
    };

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
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 1 }}>
                <Trophy size={20} />
                <Typography variant={isMobile ? "subtitle1" : "h6"}>
                    Fantasy Analysis - Top Picks
                </Typography>
            </Box>
            
            <Grid container spacing={2}>
                {fantasyData.top_fantasy_picks.slice(0, isMobile ? 6 : 10).map((player, index) => (
                    <Grid item xs={12} sm={6} md={4} key={player.player_name}>
                        <Paper 
                            sx={{ 
                                p: 2, 
                                height: '100%',
                                background: index < 3 ? `linear-gradient(135deg, ${
                                    index === 0 ? '#FFD700' : index === 1 ? '#C0C0C0' : '#CD7F32'
                                }20, transparent)` : 'inherit'
                            }}
                        >
                            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                                <Typography variant="h6" sx={{ fontSize: isMobile ? '1rem' : '1.1rem' }}>
                                    {index < 3 && <Star size={16} style={{ marginRight: 4 }} />}
                                    #{index + 1}
                                </Typography>
                                <Chip 
                                    label={player.role || 'Fielding'} 
                                    size="small" 
                                    color={getRoleColor(player.role)}
                                />
                            </Box>
                            
                            <Typography variant="subtitle1" fontWeight="bold" noWrap>
                                {player.player_name}
                            </Typography>
                            
                            <Box sx={{ my: 1 }}>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <Typography variant="body2" color="text.secondary">
                                        Expected Points
                                    </Typography>
                                    <Typography variant="h6" color="primary">
                                        {player.expected_points?.toFixed(1) || '0.0'}
                                    </Typography>
                                </Box>
                                
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1 }}>
                                    <Typography variant="body2" color="text.secondary">
                                        Confidence
                                    </Typography>
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                        <LinearProgress 
                                            variant="determinate" 
                                            value={(player.confidence || 0) * 100} 
                                            sx={{ 
                                                width: 40, 
                                                height: 6,
                                                backgroundColor: 'grey.300',
                                                '& .MuiLinearProgress-bar': {
                                                    backgroundColor: getConfidenceColor(player.confidence || 0)
                                                }
                                            }}
                                        />
                                        <Typography 
                                            variant="caption" 
                                            sx={{ color: getConfidenceColor(player.confidence || 0) }}
                                        >
                                            {((player.confidence || 0) * 100).toFixed(0)}%
                                        </Typography>
                                    </Box>
                                </Box>
                            </Box>
                            
                            {player.breakdown && (
                                <Box sx={{ mt: 1 }}>
                                    <Typography variant="caption" color="text.secondary">
                                        Bat: {player.breakdown.batting?.toFixed(1) || '0.0'} | 
                                        Bowl: {player.breakdown.bowling?.toFixed(1) || '0.0'} | 
                                        Field: {player.breakdown.fielding?.toFixed(1) || '0.0'}
                                    </Typography>
                                </Box>
                            )}
                        </Paper>
                    </Grid>
                ))}
            </Grid>
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
    endDate 
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
                    {decodeURIComponent(batting_team)} vs {decodeURIComponent(bowling_team)} Matchups
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
                            {bowlers.map(bowler => (
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
                                        <a 
                                            href={`${window.location.origin}/bowler?${new URLSearchParams({
                                                name: bowler,
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
                                            {bowler}
                                        </a>
                                    )}
                                </TableCell>
                            ))}
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {/* Batting matchup rows */}
                        {batters.map(batter => (
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
                                        cursor: 'pointer'
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
                                        {batter}
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
                        ))}
                        
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
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                        <Activity size={16} />
                                        Bowling vs Opposition
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

    React.useEffect(() => {
        if (!enabled) return;

        const fetchMatchups = async () => {
            try {
                setMatchupData(null);
                setLoading(true);
                setError(null);

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

    if (!enabled) return null;
    if (loading) return <CircularProgress />;
    if (error) return <Alert severity="error">{error}</Alert>;
    if (!matchupData) return null;
    
    if (!matchupData) {
        return <Alert severity="info">No matchup data available.</Alert>;
    }

    // Check if matchupData has the expected structure
    if (!matchupData.team1 || !matchupData.team2) {
        return <Alert severity="warning">Unexpected matchup data format.</Alert>;
    }

    // Check if there's any actual matchup data
    const hasMatchups = (
        matchupData.team1.batting_matchups && 
        Object.keys(matchupData.team1.batting_matchups).length > 0 ||
        matchupData.team2.batting_matchups && 
        Object.keys(matchupData.team2.batting_matchups).length > 0
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
            />
        </Box>
    );
};

export default Matchups;
