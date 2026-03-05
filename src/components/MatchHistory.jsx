import React, { useMemo, useState } from 'react';
import {
    Box,
    Button,
    Card,
    Chip,
    Collapse,
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

const normalizeTeam = (value) => (value || '').toString().trim().toLowerCase();

const getWinnerName = (match) => match?.winner_display || match?.winner || 'No Result';
const getTeam1Name = (match) => match?.team1_display || match?.team1 || 'Team 1';
const getTeam2Name = (match) => match?.team2_display || match?.team2 || 'Team 2';

const getWinMode = (match) => {
    if (match?.won_batting_first === true) return { label: 'Defended', color: 'primary' };
    if (match?.won_fielding_first === true) return { label: 'Chased', color: 'success' };
    if (match?.won_batting_first === false && match?.winner && match?.winner !== '-') {
        return { label: 'Chased', color: 'success' };
    }
    return { label: 'NR', color: 'default' };
};

const resolveTeamSide = (match, teamCode) => {
    if (!teamCode) return null;
    const target = normalizeTeam(teamCode);
    if (!target) return null;
    const team1Candidates = [match?.team1_display, match?.team1].map(normalizeTeam).filter(Boolean);
    const team2Candidates = [match?.team2_display, match?.team2].map(normalizeTeam).filter(Boolean);
    if (team1Candidates.includes(target)) return 'team1';
    if (team2Candidates.includes(target)) return 'team2';
    return null;
};

const getTeamResult = (match, teamCode) => {
    const side = resolveTeamSide(match, teamCode);
    const winnerCandidates = [match?.winner, match?.winner_display]
        .map(normalizeTeam)
        .filter(Boolean)
        .filter((name) => name !== '-');
    if (!side || winnerCandidates.length === 0) return 'NR';

    const teamCandidates = side === 'team1'
        ? [match?.team1, match?.team1_display]
        : [match?.team2, match?.team2_display];
    const normalizedTeamCandidates = teamCandidates.map(normalizeTeam).filter(Boolean);

    const won = winnerCandidates.some((winnerName) => normalizedTeamCandidates.includes(winnerName));
    return won ? 'W' : 'L';
};

const getMatchSummary = (match) => {
    const mode = getWinMode(match);
    return `${toDateLabel(match?.date)} • ${getWinnerName(match)} won (${mode.label})`;
};

const teamWonMatch = (match, side) => {
    const winnerCandidates = [match?.winner, match?.winner_display]
        .map(normalizeTeam)
        .filter(Boolean)
        .filter((name) => name !== '-');
    if (!winnerCandidates.length) return false;

    const teamCandidates = side === 'team1'
        ? [match?.team1, match?.team1_display]
        : [match?.team2, match?.team2_display];
    const normalizedTeamCandidates = teamCandidates.map(normalizeTeam).filter(Boolean);
    return winnerCandidates.some((winnerName) => normalizedTeamCandidates.includes(winnerName));
};

const MatchCompactRow = ({ match, indexPrefix, isMobile }) => {
    const mode = getWinMode(match);
    const team1Name = getTeam1Name(match);
    const team2Name = getTeam2Name(match);
    const team1Won = teamWonMatch(match, 'team1');
    const team2Won = teamWonMatch(match, 'team2');
    const team1Color = team1Won ? (getTeamColor(team1Name) || '#1d4ed8') : '#0f172a';
    const team2Color = team2Won ? (getTeamColor(team2Name) || '#1d4ed8') : '#0f172a';

    return (
        <Box
            key={`${indexPrefix}-${match?.id || match?.date || 'match'}`}
            sx={{
                px: 1,
                py: 0.75,
                borderRadius: 1.25,
                border: '1px solid',
                borderColor: 'divider',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 1,
            }}
        >
            <Box sx={{ minWidth: 0, flex: 1 }}>
                <Typography variant="body2" sx={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    <Box component="span" sx={{ color: 'text.secondary', fontWeight: 700 }}>
                        {toDateLabel(match?.date)}
                    </Box>
                    <Box component="span" sx={{ color: 'text.secondary', mx: 0.8 }}>
                        •
                    </Box>
                    <Box component="span" sx={{ color: team1Color, fontWeight: team1Won ? 800 : 600 }}>
                        {`${team1Name} ${match?.score1 || '-'}`}
                    </Box>
                    <Box component="span" sx={{ color: 'text.secondary', mx: 0.7 }}>
                        vs
                    </Box>
                    <Box component="span" sx={{ color: team2Color, fontWeight: team2Won ? 800 : 600 }}>
                        {`${team2Name} ${match?.score2 || '-'}`}
                    </Box>
                </Typography>
            </Box>
            {!isMobile && <Chip size="small" color={mode.color} label={mode.label} />}
        </Box>
    );
};

const TeamSplitHeader = ({ team1, team2, stats, isMobile }) => {
    const [showDetails, setShowDetails] = useState(false);
    const team1Wins = stats?.team1_wins || 0;
    const team2Wins = stats?.team2_wins || 0;
    const draws = stats?.draws || 0;
    const total = team1Wins + team2Wins + draws;
    const recentH2H = stats?.recent_matches || [];
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
            <Box sx={{ mt: 1.05 }}>
                <Button
                    size="small"
                    onClick={() => setShowDetails((prev) => !prev)}
                    disabled={recentH2H.length === 0}
                    sx={{ px: 0, textTransform: 'none', fontWeight: 700 }}
                >
                    {showDetails ? 'Hide H2H details' : `Show H2H details (${recentH2H.length})`}
                </Button>
            </Box>
            <Collapse in={showDetails} timeout="auto" unmountOnExit>
                <Box sx={{ mt: 0.9, display: 'flex', flexDirection: 'column', gap: 0.75 }}>
                    {recentH2H.map((match, index) => (
                        <MatchCompactRow
                            key={`h2h-${match?.id || match?.date || index}`}
                            match={match}
                            indexPrefix="h2h"
                            isMobile={isMobile}
                        />
                    ))}
                </Box>
            </Collapse>
            {recentH2H.length === 0 && (
                <Box sx={{ mt: 0.9 }}>
                    <Typography variant="caption" color="text.secondary">
                        No recent H2H data available.
                    </Typography>
                </Box>
            )}
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
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75 }}>
                {matches.map((match, index) => (
                    <MatchCompactRow
                        key={`venue-${match?.id || match?.date || index}`}
                        match={match}
                        indexPrefix="venue"
                        isMobile={isMobile}
                    />
                ))}
            </Box>
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

const TeamFormRow = ({ teamCode, matches, isMobile, onTileSelect }) => {
    const teamColor = getTeamColor(teamCode) || '#1d4ed8';
    const tileSize = isMobile ? 24 : 26;

    const formTiles = useMemo(
        () => (matches || []).map((match) => ({
            match,
            result: getTeamResult(match, teamCode),
        })),
        [matches, teamCode]
    );

    return (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: isMobile ? 0.9 : 1.1, minWidth: 0, width: '100%' }}>
            <Typography
                variant="body2"
                sx={{
                    minWidth: isMobile ? 66 : 78,
                    fontWeight: 700,
                    color: teamColor,
                    whiteSpace: 'nowrap',
                }}
            >
                {teamCode}
            </Typography>
            {!formTiles.length ? (
                <Typography variant="body2" color="text.secondary" sx={{ ml: 'auto' }}>
                    N/A
                </Typography>
            ) : (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.45, minWidth: 0, ml: 'auto', justifyContent: 'flex-end' }}>
                    {formTiles.map(({ match, result }, index) => {
                        const style = resultTileStyles[result] || resultTileStyles.NR;
                        const tile = (
                            <Box
                                component="button"
                                key={`${teamCode}-${match?.id || match?.date || 'form'}-${index}`}
                                onClick={() => {
                                    if (isMobile) {
                                        onTileSelect({ teamCode, match, result });
                                    }
                                }}
                                sx={{
                                    width: tileSize,
                                    minWidth: tileSize,
                                    height: tileSize,
                                    border: '1px solid',
                                    borderColor: style.border,
                                    borderRadius: 0.8,
                                    bgcolor: style.bg,
                                    color: style.color,
                                    fontWeight: 800,
                                    fontSize: isMobile ? '0.73rem' : '0.76rem',
                                    lineHeight: 1,
                                    cursor: isMobile ? 'pointer' : 'default',
                                    p: 0,
                                }}
                            >
                                {result}
                            </Box>
                        );

                        if (isMobile) {
                            return tile;
                        }

                        return (
                            <Tooltip
                                key={`${teamCode}-${match?.id || match?.date || 'form-tip'}-${index}`}
                                title={<FormTileDetails match={match} teamCode={teamCode} result={result} />}
                                arrow
                            >
                                {tile}
                            </Tooltip>
                        );
                    })}
                </Box>
            )}
        </Box>
    );
};

const TeamFormCard = ({ team1, team2, team1Matches, team2Matches, isMobile }) => {
    const [selectedMatch, setSelectedMatch] = useState(null);

    return (
        <>
            <Card sx={{ p: isMobile ? 1.5 : 2, border: '1px solid', borderColor: 'divider', boxShadow: 'none' }}>
                <Typography variant={isMobile ? 'subtitle2' : 'h6'} sx={{ fontWeight: 700 }}>
                    Form
                </Typography>
                <Box sx={{ mt: 1.1, display: 'flex', flexDirection: 'column', gap: 1 }}>
                    <TeamFormRow
                        teamCode={team1}
                        matches={team1Matches || []}
                        isMobile={isMobile}
                        onTileSelect={setSelectedMatch}
                    />
                    <TeamFormRow
                        teamCode={team2}
                        matches={team2Matches || []}
                        isMobile={isMobile}
                        onTileSelect={setSelectedMatch}
                    />
                </Box>
            </Card>

            <Dialog open={Boolean(selectedMatch)} onClose={() => setSelectedMatch(null)} fullWidth maxWidth="xs">
                <DialogTitle sx={{ fontWeight: 700 }}>
                    {selectedMatch ? `${selectedMatch.teamCode} Match Details` : 'Match Details'}
                </DialogTitle>
                <DialogContent>
                    {selectedMatch && (
                        <FormTileDetails
                            match={selectedMatch.match}
                            teamCode={selectedMatch.teamCode}
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
            <Grid item xs={12}>
                <TeamFormCard
                    team1={team1}
                    team2={team2}
                    team1Matches={team1Results}
                    team2Matches={team2Results}
                    isMobile={isMobile}
                />
            </Grid>
        </Grid>
    </Box>
);

export default MatchHistory;
