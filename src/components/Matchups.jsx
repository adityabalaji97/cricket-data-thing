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
    Tooltip
} from '@mui/material';

import { Info as InfoIcon } from 'lucide-react';

const MetricCell = ({ data, isMobile, bowler }) => {
    if (!data) return <TableCell align="center">-</TableCell>;

    const getColor = (sr, balls) => {
        if (balls < 6) return 'text.secondary';
        if (sr >= 150) return 'success.main';
        if (sr <= 100) return 'error.main';
        return 'warning.main';
    };

    let displayValue;

    if (bowler === "Overall") {
        // Calculate effective wickets to avoid division by zero
        const effectiveWickets = data.wickets && data.wickets > 0 ? data.wickets : 1;
        // Display average (balls per wicket) @ strike rate.
        displayValue = data.average 
            ? `${data.average.toFixed(1)} (${(data.balls / effectiveWickets).toFixed(1)}) @ ${data.strike_rate.toFixed(1)}`
            : "-";
    } else {
        displayValue = isMobile
            ? `${data.runs}-${data.wickets} (${data.balls})`
            : `${data.runs}-${data.wickets} (${data.balls}) @ ${data.strike_rate.toFixed(1)}`;
    }

    return (
        <TableCell 
            align="center" 
            sx={{ 
                color: getColor(data.strike_rate, data.balls),
                fontSize: isMobile ? '0.75rem' : '0.875rem',
                padding: isMobile ? '4px' : '8px'
            }}
        >
            <Tooltip
                title={
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
                }
            >
                <Box>{displayValue}</Box>
            </Tooltip>
        </TableCell>
    );
};

const MatchupMatrix = ({ batting_team, bowling_team, matchups, isMobile, venue, startDate, endDate }) => {
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
        <Card sx={{ p: 2, mb: 3 }}>
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
                                        bowler={bowler} // pass the bowler to MetricCell
                                    />
                                ))}
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>
        </Card>
    );
};

const Matchups = ({ team1, team2, startDate, endDate, team1_players, team2_players, isMobile }) => {
    const [matchupData, setMatchupData] = React.useState(null);
    const [loading, setLoading] = React.useState(false);
    const [error, setError] = React.useState(null);

    React.useEffect(() => {
        const fetchMatchups = async () => {
            try {
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
    }, [team1, team2, startDate, endDate, team1_players, team2_players]);

    if (loading) return <CircularProgress />;
    if (error) return <Alert severity="error">{error}</Alert>;
    if (!matchupData) return null;
    
    // In Matchups.jsx, update the hasMatchups check
    console.log("matchupData:", matchupData);

    if (!matchupData) {
    console.log("No matchupData returned from API");
    return <Alert severity="info">No matchup data available.</Alert>;
    }

    // Check if matchupData has the expected structure
    if (!matchupData.team1 || !matchupData.team2) {
    console.log("matchupData missing team structure:", matchupData);
    return <Alert severity="warning">Unexpected matchup data format.</Alert>;
    }

    // Check if there's any actual matchup data
    const hasMatchups = (
    matchupData.team1.batting_matchups && 
    Object.keys(matchupData.team1.batting_matchups).length > 0 ||
    matchupData.team2.batting_matchups && 
    Object.keys(matchupData.team2.batting_matchups).length > 0
    );

    console.log("hasMatchups check result:", hasMatchups);

    if (!hasMatchups) {
    return (
        <Alert severity="info" sx={{ mt: 3 }}>
        No matchup data found between these players in the selected time period.
        </Alert>
    );
    }

    return (
        <Box sx={{ mt: 3 }}>
            <MatchupMatrix 
                batting_team={matchupData.team1.name}
                bowling_team={matchupData.team2.name}
                matchups={matchupData.team1.batting_matchups}
                isMobile={isMobile}
                venue={matchupData.venue}
                startDate={startDate}
                endDate={endDate}
            />
            <MatchupMatrix 
                batting_team={matchupData.team2.name}
                bowling_team={matchupData.team1.name}
                matchups={matchupData.team2.batting_matchups}
                isMobile={isMobile}
                venue={matchupData.venue}
                startDate={startDate}
                endDate={endDate}
            />
        </Box>
    );
};

export default Matchups;