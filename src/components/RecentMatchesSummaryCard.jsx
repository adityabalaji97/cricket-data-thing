import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  Grid,
  Typography,
  useMediaQuery,
  useTheme
} from '@mui/material';
import { Link } from 'react-router-dom';
import SportsCricketIcon from '@mui/icons-material/SportsCricket';
import StadiumIcon from '@mui/icons-material/Stadium';
import GroupsIcon from '@mui/icons-material/Groups';
import CalendarTodayIcon from '@mui/icons-material/CalendarToday';
import axios from 'axios';
import config from '../config';

const formatDate = (dateString) => {
  if (!dateString) return 'Unknown';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  });
};

const matchTitle = (match) => `${match.team1} vs ${match.team2}`;

const MatchListCard = ({ match, compact = false }) => (
  <Card
    variant="outlined"
    sx={{
      height: '100%',
      borderRadius: 2,
      transition: 'transform 0.2s, box-shadow 0.2s',
      '&:hover': {
        transform: { xs: 'none', md: 'translateY(-2px)' },
        boxShadow: { xs: 0, md: 3 }
      }
    }}
  >
    <CardContent sx={{ p: compact ? 1.25 : 1.75, '&:last-child': { pb: compact ? 1.25 : 1.75 } }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 1, mb: 0.75 }}>
        <Chip
          label={match.competition_abbr || match.competition_display || match.competition}
          size="small"
          color={match.is_international ? 'primary' : 'default'}
          sx={{ height: 22, fontSize: '0.7rem', fontWeight: 700 }}
        />
        <Typography variant="caption" color="text.secondary" sx={{ whiteSpace: 'nowrap', mt: 0.25 }}>
          {formatDate(match.date)}
        </Typography>
      </Box>

      <Typography variant="subtitle2" fontWeight={800} sx={{ mb: 0.75, lineHeight: 1.25 }}>
        {matchTitle(match)}
      </Typography>

      {match.winner && (
        <Typography variant="caption" sx={{ color: 'success.main', fontWeight: 700, display: 'block', mb: 0.5 }}>
          Winner: {match.winner}
        </Typography>
      )}

      {match.venue && (
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', lineHeight: 1.35 }}>
          {match.venue}
        </Typography>
      )}

      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75, mt: 1.25 }}>
        {match.match_id && (
          <Button
            size="small"
            variant="contained"
            startIcon={<SportsCricketIcon />}
            component={Link}
            to={`/scorecard/${match.match_id}`}
            sx={{ fontSize: '0.72rem', py: 0.35, px: 1 }}
          >
            Scorecard
          </Button>
        )}
        <Button
          size="small"
          variant="outlined"
          startIcon={<StadiumIcon />}
          component={Link}
          to={`/venue?venue=${encodeURIComponent(match.venue || '')}&team1=${encodeURIComponent(match.team1)}&team2=${encodeURIComponent(match.team2)}`}
          sx={{ fontSize: '0.72rem', py: 0.35, px: 1 }}
        >
          Venue
        </Button>
        <Button
          size="small"
          variant="outlined"
          startIcon={<GroupsIcon />}
          component={Link}
          to={`/matchups?team1=${encodeURIComponent(match.team1)}&team2=${encodeURIComponent(match.team2)}`}
          sx={{ fontSize: '0.72rem', py: 0.35, px: 1 }}
        >
          H2H
        </Button>
      </Box>
    </CardContent>
  </Card>
);

const RecentMatchesSummaryCard = () => {
  const [activeCompetition, setActiveCompetition] = useState('all');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  useEffect(() => {
    let cancelled = false;

    const fetchDiscovery = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await axios.get(`${config.API_URL}/recent-matches/discover`, {
          params: { competition: activeCompetition, limit: 12, offset: 0, per_group: 3 }
        });
        if (!cancelled) setData(response.data);
      } catch (err) {
        console.error('Error fetching recent scorecards:', err);
        if (!cancelled) setError('Failed to load recent scorecards');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchDiscovery();
    return () => {
      cancelled = true;
    };
  }, [activeCompetition]);

  const filters = useMemo(() => {
    const source = data?.filters || [];
    return source.slice(0, isMobile ? 8 : 12);
  }, [data, isMobile]);

  const competitionStats = useMemo(() => (
    Object.values(data?.competition_stats || {})
      .sort((a, b) => {
        if (a.priority !== b.priority) return a.priority - b.priority;
        return (b.match_count || 0) - (a.match_count || 0);
      })
  ), [data]);

  const handleLoadMore = async () => {
    if (!data?.has_more || data.next_offset == null || activeCompetition === 'all') return;
    try {
      setLoadingMore(true);
      const response = await axios.get(`${config.API_URL}/recent-matches/discover`, {
        params: {
          competition: activeCompetition,
          limit: data.limit || 12,
          offset: data.next_offset,
          per_group: 3
        }
      });
      setData((prev) => ({
        ...response.data,
        matches: [...(prev?.matches || []), ...(response.data.matches || [])]
      }));
    } catch (err) {
      console.error('Error loading more scorecards:', err);
      setError('Failed to load more scorecards');
    } finally {
      setLoadingMore(false);
    }
  };

  if (loading) {
    return (
      <Card sx={{ mb: 4, borderRadius: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 160 }}>
            <CircularProgress size={24} />
            <Typography sx={{ ml: 2 }}>Loading recent scorecards...</Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  if (error && !data) {
    return (
      <Card sx={{ mb: 4, borderRadius: 3 }}>
        <CardContent>
          <Alert severity="error">{error}</Alert>
        </CardContent>
      </Card>
    );
  }

  if (!data) return null;

  return (
    <Card
      sx={{
        mb: 4,
        background: 'linear-gradient(135deg, #f5f9ff 0%, #e6eff8 100%)',
        borderRadius: 3,
        boxShadow: '0 8px 28px rgba(16, 60, 110, 0.12)'
      }}
    >
      <CardContent sx={{ p: { xs: 1.5, md: 3 } }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 1.5, alignItems: 'center', mb: 1.5 }}>
          <Box>
            <Typography variant={isMobile ? 'h6' : 'h5'} fontWeight={900} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <SportsCricketIcon color="primary" />
              Recent Scorecards
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Browse the newest T20 scorecards by competition
            </Typography>
          </Box>
          <Chip
            size="small"
            color="primary"
            label={data.mode === 'filtered' ? `${data.total} matches` : `${data.total_matches} matches`}
          />
        </Box>

        <Box sx={{ display: 'flex', gap: 1, overflowX: 'auto', pb: 1, mb: 1.5 }}>
          {filters.map((filter) => (
            <Chip
              key={filter.key}
              label={filter.label}
              clickable
              color={activeCompetition === filter.key ? 'primary' : 'default'}
              variant={activeCompetition === filter.key ? 'filled' : 'outlined'}
              onClick={() => setActiveCompetition(filter.key)}
              sx={{ flexShrink: 0, fontWeight: 700 }}
            />
          ))}
        </Box>

        {error && (
          <Alert severity="warning" sx={{ mb: 2 }}>{error}</Alert>
        )}

        {data.mode === 'grouped' ? (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {(data.groups || []).slice(0, isMobile ? 5 : 8).map((group) => (
              <Box key={group.key}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                  <Typography variant="subtitle1" fontWeight={900}>
                    {group.label}
                  </Typography>
                  {group.has_more && (
                    <Button size="small" onClick={() => setActiveCompetition(group.key)}>
                      View more
                    </Button>
                  )}
                </Box>
                <Grid container spacing={1.25}>
                  {(group.matches || []).map((match) => (
                    <Grid item xs={12} md={4} key={match.match_id}>
                      <MatchListCard match={match} compact={isMobile} />
                    </Grid>
                  ))}
                </Grid>
              </Box>
            ))}
          </Box>
        ) : (
          <Box>
            <Grid container spacing={1.25}>
              {(data.matches || []).map((match) => (
                <Grid item xs={12} md={4} key={match.match_id}>
                  <MatchListCard match={match} compact={isMobile} />
                </Grid>
              ))}
            </Grid>
            {data.has_more && (
              <Box sx={{ textAlign: 'center', mt: 2 }}>
                <Button
                  variant="outlined"
                  onClick={handleLoadMore}
                  disabled={loadingMore}
                  startIcon={loadingMore ? <CircularProgress size={16} /> : <CalendarTodayIcon />}
                >
                  {loadingMore ? 'Loading...' : 'Load more'}
                </Button>
              </Box>
            )}
          </Box>
        )}

        {!!competitionStats.length && (
          <>
            <Divider sx={{ my: 2.5 }} />
            <Typography variant="subtitle1" fontWeight={900} sx={{ mb: 1 }}>
              League Match Counts
            </Typography>
            <Grid container spacing={1}>
              {competitionStats.slice(0, isMobile ? 6 : 10).map((comp) => (
                <Grid item xs={6} sm={4} md={3} key={comp.competition_key || comp.competition}>
                  <Button
                    fullWidth
                    variant={activeCompetition === comp.competition_key ? 'contained' : 'outlined'}
                    onClick={() => setActiveCompetition(comp.competition_key || comp.competition)}
                    sx={{
                      display: 'block',
                      textAlign: 'center',
                      py: 1,
                      borderRadius: 2,
                      textTransform: 'none',
                      minHeight: 92
                    }}
                  >
                    <Typography component="span" display="block" fontWeight={900}>
                      {comp.competition_display}
                    </Typography>
                    <Typography component="span" display="block" variant="h6" fontWeight={900}>
                      {(comp.match_count || 0).toLocaleString()}
                    </Typography>
                    <Typography component="span" display="block" variant="caption">
                      Latest: {formatDate(comp.latest_date)}
                    </Typography>
                  </Button>
                </Grid>
              ))}
            </Grid>
          </>
        )}
      </CardContent>
    </Card>
  );
};

export default RecentMatchesSummaryCard;
