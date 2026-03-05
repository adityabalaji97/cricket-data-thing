import React, { useMemo, useState } from 'react';
import {
    Box,
    Card,
    Chip,
    Dialog,
    DialogContent,
    DialogTitle,
    Grid,
    Tooltip,
    Typography,
} from '@mui/material';
import { getTeamColor } from '../utils/teamColors';

const DATE_FORMATTER = new Intl.DateTimeFormat('en-IN', {
    day: '2-digit',
    month: 'short',
    year: '2-digit',
});

const resultTileStyles = {
    W: { bg: '#16a34a', color: '#ffffff', border: '#15803d' },
    L: { bg: '#dc2626', color: '#ffffff', border: '#b91c1c' },
    NR: { bg: '#64748b', color: '#ffffff', border: '#475569' },
};

const toDateLabel = (isoDate) => {
    if (!isoDate) return 'Date N/A';
    const parsed = new Date(isoDate);
    if (Number.isNaN(parsed.getTime())) return 'Date N/A';
    return DATE_FORMATTER.format(parsed);
};

const getWinnerName = (match) => match?.winner_display || match?.winner || 'No Result';
const getTeam1Name = (match) => match?.team1_display || match?.team1 || 'Team 1';
const getTeam2Name = (match) => match?.team2_display || match?.team2 || 'Team 2';

const getWinMode = (match) => {
    if (match?.won_batting_first === true) return { label: 'Defended', color: 'primary' };
    if (match?.won_fielding_first === true) return { label: 'Chased', color: 'success' };
    return { label: 'NR', color: 'default' };
};

const resolveTeamSide = (match, teamCode) => {
    if (!teamCode) return null;
    if (teamCode === match?.team1_display || teamCode === match?.team1) return 'team1';
    if (teamCode === match?.team2_display || teamCode === match?.team2) return 'team2';
    return null;
};

const getTeamResult = (match, teamCode) => {
    const side = resolveTeamSide(match, teamCode);
    if (!side || !match?.winner) return 'NR';

    const won = side === 'team1'
        ? match.winner === match.team1 || match.winner_display === match.team1_display
        : match.winner === match.team2 || match.winner_display === match.team2_display;
    return won ? 'W' : 'L';
};

const getMatchSummary = (match) => {
    const mode = getWinMode(match);
    return `${toDateLabel(match?.date)} • ${getWinnerName(match)} won (${mode.label})`;
};

const TeamSplitHeader = ({ team1, team2, stats, isMobile }) => {
    const team1Wins = stats?.team1_wins || 0;
    const team2Wins = stats?.team2_wins || 0;
    const draws = stats?.draws || 0;
    const total = team1Wins + team2Wins + draws;
    const team1Color = getTeamColor(team1) || '#1d4ed8';
    const team2Color = getTeamColor(team2) || '#7c3aed';

    const percentages = {
        team1: total > 0 ? (team1Wins * 100.0) / total : 0,
        draws: total > 0 ? (draws * 100.0) / total : 0,
        team2: total > 0 ? (team2Wins * 100.0) / total : 0,
    };

    return (
        <Card sx={{ p: isMobile ? 1.5 : 2, height: '100%', border: '1px solid', borderColor: 'divider', boxShadow: 'none' }}>
            <Typography variant={isMobile ? 'subtitle1' : 'h6'} sx={{ fontWeight: 700 }}>
                Head to Head
            </Typography>
            <Box sx={{ mt: 1.2, display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', textAlign: 'center', gap: 1 }}>
                <Box>
                    <Typography sx={{ color: team1Color, fontWeight: 800, fontSize: isMobile ? '1.35rem' : '1.55rem' }}>
                        {team1Wins}
                    </Typography>
                    <Typography variant="caption" sx={{ color: team1Color, fontWeight: 700 }}>
                        {team1}
                    </Typography>
                    <Typography variant="caption" display="block" color="text.secondary">
                        {percentages.team1.toFixed(0)}%
                    </Typography>
                </Box>
                <Box>
                    <Typography sx={{ color: '#475569', fontWeight: 800, fontSize: isMobile ? '1.35rem' : '1.55rem' }}>
                        {draws}
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#475569', fontWeight: 700 }}>
                        NR
                    </Typography>
                    <Typography variant="caption" display="block" color="text.secondary">
                        {percentages.draws.toFixed(0)}%
                    </Typography>
                </Box>
                <Box>
                    <Typography sx={{ color: team2Color, fontWeight: 800, fontSize: isMobile ? '1.35rem' : '1.55rem' }}>
                        {team2Wins}
                    </Typography>
                    <Typography variant="caption" sx={{ color: team2Color, fontWeight: 700 }}>
                        {team2}
                    </Typography>
                    <Typography variant="caption" display="block" color="text.secondary">
                        {percentages.team2.toFixed(0)}%
                    </Typography>
                </Box>
            </Box>
            <Box sx={{ mt: 1.2 }}>
                <Box sx={{ display: 'flex', width: '100%', height: 16, borderRadius: 999, overflow: 'hidden', bgcolor: '#e2e8f0' }}>
                    {total > 0 ? (
                        <>
                            {team1Wins > 0 && <Box sx={{ flex: `${team1Wins} 1 0`, bgcolor: team1Color }} />}
                            {draws > 0 && <Box sx={{ flex: `${draws} 1 0`, bgcolor: '#94a3b8' }} />}
                            {team2Wins > 0 && <Box sx={{ flex: `${team2Wins} 1 0`, bgcolor: team2Color }} />}
                        </>
                    ) : (
                        <Box sx={{ flex: 1, bgcolor: '#cbd5e1' }} />
                    )}
                </Box>
            </Box>
            <Box sx={{ mt: 1.3, display: 'flex', flexDirection: 'column', gap: 0.75 }}>
                {(stats?.recent_matches || []).slice(0, 4).map((match, index) => {
                    const mode = getWinMode(match);
                    return (
                        <Box
                            key={`${match?.id || match?.date || 'h2h'}-${index}`}
                            sx={{
                                px: 1,
                                py: 0.85,
                                borderRadius: 1.25,
                                border: '1px solid',
                                borderColor: 'divider',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                gap: 1,
                            }}
                        >
                            <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                {`${getTeam1Name(match)} ${match?.score1 || '-'} vs ${getTeam2Name(match)} ${match?.score2 || '-'}`}
                            </Typography>
                            <Chip size="small" color={mode.color} label={mode.label} />
                        </Box>
                    );
                })}
            </Box>
        </Card>
    );
};

const VenueRecentMatches = ({ venue, matches, isMobile }) => (
    <Card sx={{ p: isMobile ? 1.5 : 2, height: '100%', border: '1px solid', borderColor: 'divider', boxShadow: 'none' }}>
        <Typography variant={isMobile ? 'subtitle1' : 'h6'} sx={{ fontWeight: 700, mb: 1.2 }}>
            {`Recent at ${venue}`}
        </Typography>
        {!matches?.length ? (
            <Typography variant="body2" color="text.secondary">
                No recent matches found for this venue.
            </Typography>
        ) : (
            <Grid container spacing={1}>
                {matches.map((match, index) => {
                    const mode = getWinMode(match);
                    return (
                        <Grid item xs={12} sm={6} key={`${match?.id || match?.date || 'venue'}-${index}`}>
                            <Box sx={{ p: 1.1, borderRadius: 1.5, border: '1px solid', borderColor: 'divider', bgcolor: 'background.paper' }}>
                                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 0.8 }}>
                                    <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700 }}>
                                        {toDateLabel(match?.date)}
                                    </Typography>
                                    <Chip size="small" color={mode.color} label={mode.label} />
                                </Box>
                                <Typography variant="body2" sx={{ mt: 0.8, fontWeight: 700 }}>
                                    {`${getWinnerName(match)} won`}
                                </Typography>
                                <Typography variant="caption" color="text.secondary">
                                    {`${getTeam1Name(match)} ${match?.score1 || '-'} vs ${getTeam2Name(match)} ${match?.score2 || '-'}`}
                                </Typography>
                            </Box>
                        </Grid>
                    );
                })}
            </Grid>
        )}
    </Card>
);

const FormTileDetails = ({ match, teamCode, result }) => (
    <Box sx={{ maxWidth: 260 }}>
        <Typography variant="body2" sx={{ fontWeight: 700 }}>
            {`${teamCode}: ${result}`}
        </Typography>
        <Typography variant="caption" display="block">
            {getMatchSummary(match)}
        </Typography>
        <Typography variant="caption" display="block">
            {`${getTeam1Name(match)} ${match?.score1 || '-'} vs ${getTeam2Name(match)} ${match?.score2 || '-'}`}
        </Typography>
        <Typography variant="caption" display="block">
            {match?.venue || 'Venue N/A'}
        </Typography>
    </Box>
);

const TeamFormStrip = ({ teamCode, matches, isMobile }) => {
    const [selectedMatch, setSelectedMatch] = useState(null);
    const teamColor = getTeamColor(teamCode) || '#1d4ed8';

    const formTiles = useMemo(
        () => (matches || []).map((match) => ({
            match,
            result: getTeamResult(match, teamCode),
        })),
        [matches, teamCode]
    );

    return (
        <>
            <Card sx={{ p: isMobile ? 1.5 : 2, border: '1px solid', borderColor: 'divider', boxShadow: 'none' }}>
                <Typography variant={isMobile ? 'subtitle1' : 'h6'} sx={{ fontWeight: 700, color: teamColor }}>
                    {`${teamCode} Recent Form`}
                </Typography>
                {!formTiles.length ? (
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                        No recent matches found.
                    </Typography>
                ) : (
                    <Box sx={{ mt: 1.2, display: 'flex', alignItems: 'center', gap: 0.9, overflowX: 'auto', pb: 0.4 }}>
                        {formTiles.map(({ match, result }, index) => {
                            const style = resultTileStyles[result] || resultTileStyles.NR;
                            const tile = (
                                <Box
                                    component="button"
                                    onClick={() => {
                                        if (isMobile) setSelectedMatch({ match, result });
                                    }}
                                    key={`${match?.id || match?.date || 'form'}-${index}`}
                                    sx={{
                                        width: 40,
                                        minWidth: 40,
                                        height: 40,
                                        border: '1px solid',
                                        borderColor: style.border,
                                        borderRadius: 1.25,
                                        bgcolor: style.bg,
                                        color: style.color,
                                        fontWeight: 800,
                                        fontSize: '0.95rem',
                                        cursor: isMobile ? 'pointer' : 'default',
                                    }}
                                >
                                    {result}
                                </Box>
                            );

                            if (isMobile) return tile;
                            return (
                                <Tooltip key={`${match?.id || match?.date || 'form-tip'}-${index}`} title={<FormTileDetails match={match} teamCode={teamCode} result={result} />} arrow>
                                    {tile}
                                </Tooltip>
                            );
                        })}
                    </Box>
                )}
            </Card>

            <Dialog open={Boolean(selectedMatch)} onClose={() => setSelectedMatch(null)} fullWidth maxWidth="xs">
                <DialogTitle sx={{ fontWeight: 700 }}>{`${teamCode} Match Details`}</DialogTitle>
                <DialogContent>
                    {selectedMatch && (
                        <FormTileDetails
                            match={selectedMatch.match}
                            teamCode={teamCode}
                            result={selectedMatch.result}
                        />
                    )}
                </DialogContent>
            </Dialog>
        </>
    );
};

const MatchHistory = ({ venue, team1, team2, venueResults, team1Results, team2Results, h2hStats, isMobile }) => (
    <Box sx={{ mt: 1 }}>
        <Grid container spacing={1.5}>
            <Grid item xs={12} lg={6}>
                <TeamSplitHeader team1={team1} team2={team2} stats={h2hStats} isMobile={isMobile} />
            </Grid>
            <Grid item xs={12} lg={6}>
                <VenueRecentMatches venue={venue} matches={venueResults || []} isMobile={isMobile} />
            </Grid>
            <Grid item xs={12} md={6}>
                <TeamFormStrip teamCode={team1} matches={team1Results || []} isMobile={isMobile} />
            </Grid>
            <Grid item xs={12} md={6}>
                <TeamFormStrip teamCode={team2} matches={team2Results || []} isMobile={isMobile} />
            </Grid>
        </Grid>
    </Box>
);

export default MatchHistory;
