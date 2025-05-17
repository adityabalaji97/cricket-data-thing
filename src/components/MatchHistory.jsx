import React from 'react';
import { Box, Card, Typography, Divider, Grid } from '@mui/material';

const HeadToHeadStats = ({ team1, team2, stats, isMobile }) => {
    if (!stats) return null;
    
    return (
        <Card sx={{ mb: 2, p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
            <Typography variant={isMobile ? "h6" : "h5"} gutterBottom>
                Head to Head Stats
            </Typography>
            <Box sx={{ 
                display: 'flex', 
                justifyContent: 'space-around', 
                textAlign: 'center',
                py: 2
            }}>
                <Box>
                    <Typography variant={isMobile ? "h5" : "h3"} color="primary">
                        {stats.team1_wins || 0}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                        {team1} wins
                    </Typography>
                </Box>
                <Box>
                    <Typography variant={isMobile ? "h5" : "h3"}>
                        {stats.draws || 0}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                        No Result
                    </Typography>
                </Box>
                <Box>
                    <Typography variant={isMobile ? "h5" : "h3"} color="secondary">
                        {stats.team2_wins || 0}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                        {team2} wins
                    </Typography>
                </Box>
            </Box>
            <Divider />
            <Box sx={{ mt: 2, flex: 1, overflowY: 'auto' }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="subtitle2">Recent Head to Head</Typography>
                    <Typography variant="subtitle2" color="text.secondary" sx={{ width: '80px' }}>Result</Typography>
                </Box>
                {stats.recent_matches?.map((match, index) => (
                    <Box
                        key={match.date + index}
                        sx={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            p: 1,
                            backgroundColor: index % 2 === 1 ? 'rgba(0,0,0,0.02)' : 'transparent',
                            borderRadius: 1,
                        }}
                    >
                        <Box sx={{ flex: 1 }}>
                            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                                <Typography sx={{ 
                                    fontWeight: match.winner === match.team1 ? 'bold' : 'normal',
                                    color: match.winner === match.team1 ? 'primary.main' : 'text.primary'
                                }}>
                                    {match.team1} {match.score1}
                                </Typography>
                                <Typography>vs</Typography>
                                <Typography sx={{ 
                                    fontWeight: match.winner === match.team2 ? 'bold' : 'normal',
                                    color: match.winner === match.team2 ? 'primary.main' : 'text.primary'
                                }}>
                                    {match.team2} {match.score2}
                                </Typography>
                            </Box>
                            <Typography variant="caption" color="text.secondary">
                                {new Date(match.date).toLocaleDateString()}
                                {match.venue && ` • ${match.venue}`}
                            </Typography>
                        </Box>
                        <Typography variant="body2" color="text.secondary" sx={{ width: '80px', textAlign: 'right' }}>
                            {match.won_batting_first ? "Bat 1st" : "Chased"}
                        </Typography>
                    </Box>
                ))}
            </Box>
        </Card>
    );
};

const ResultsSection = ({ title, matches, showVenue = true, isMobile }) => (
    <Card sx={{ mb: 2, p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
        <Typography variant={isMobile ? "subtitle1" : "h6"} gutterBottom>
            {title}
        </Typography>
        <Box sx={{ flex: 1, overflowY: 'auto' }}>
            {matches.map((match, index) => (
                <Box
                    key={match.date + index}
                    sx={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        p: 1,
                        backgroundColor: index % 2 === 1 ? 'rgba(0,0,0,0.02)' : 'transparent',
                        borderRadius: 1,
                    }}
                >
                    <Box sx={{ flex: 1 }}>
                        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                            <Typography sx={{ 
                                fontWeight: match.winner === match.team1 ? 'bold' : 'normal',
                                color: match.winner === match.team1 ? 'primary.main' : 'text.primary'
                            }}>
                                {match.team1} {match.score1}
                            </Typography>
                            <Typography>vs</Typography>
                            <Typography sx={{ 
                                fontWeight: match.winner === match.team2 ? 'bold' : 'normal',
                                color: match.winner === match.team2 ? 'primary.main' : 'text.primary'
                            }}>
                                {match.team2} {match.score2}
                            </Typography>
                        </Box>
                        <Typography variant="caption" color="text.secondary">
                            {new Date(match.date).toLocaleDateString()}
                            {showVenue && match.venue && ` • ${match.venue}`}
                        </Typography>
                    </Box>
                    {match.winner && (
                        <Typography variant="body2" color="text.secondary" sx={{ width: '80px', textAlign: 'right' }}>
                            {match.won_batting_first ? "Bat 1st" : "Chased"}
                        </Typography>
                    )}
                </Box>
            ))}
        </Box>
    </Card>
);

const MatchHistory = ({ venue, team1, team2, venueResults, team1Results, team2Results, h2hStats, isMobile }) => (
    <Box sx={{ mt: 3 }}>
        <Grid container spacing={2}>
            <Grid item xs={12} lg={6}>
                <HeadToHeadStats 
                    team1={team1} 
                    team2={team2} 
                    stats={h2hStats} 
                    isMobile={isMobile}
                />
            </Grid>
            <Grid item xs={12} lg={6}>
                <ResultsSection 
                    title={`Recent matches at ${venue}`}
                    matches={venueResults}
                    showVenue={false}
                    isMobile={isMobile}
                />
            </Grid>
            <Grid item xs={12} md={6}>
                <ResultsSection 
                    title={`${team1} - Recent Form`}
                    matches={team1Results} 
                    isMobile={isMobile}
                />
            </Grid>
            <Grid item xs={12} md={6}>
                <ResultsSection 
                    title={`${team2} - Recent Form`}
                    matches={team2Results} 
                    isMobile={isMobile}
                />
            </Grid>
        </Grid>
    </Box>
);

export default MatchHistory;