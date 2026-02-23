import React, { useMemo, useState } from 'react';
import axios from 'axios';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Container,
  Grid,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import config from '../config';

const TODAY = new Date().toISOString().split('T')[0];
const DEFAULT_START = `${new Date().getFullYear() - 1}-01-01`;

const PairTable = ({ title, rows = [], role }) => (
  <Box>
    <Typography variant="h6" sx={{ mb: 1 }}>{title}</Typography>
    <TableContainer component={Paper} variant="outlined">
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>#</TableCell>
            <TableCell>Player 1</TableCell>
            <TableCell>Player 2</TableCell>
            <TableCell align="right">Distance</TableCell>
            <TableCell align="right">{role === 'batter' ? 'Innings' : 'Balls'} (P1)</TableCell>
            <TableCell align="right">{role === 'batter' ? 'Innings' : 'Balls'} (P2)</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row, idx) => (
            <TableRow key={`${row.player1}-${row.player2}-${idx}`}>
              <TableCell>{idx + 1}</TableCell>
              <TableCell>{row.player1}</TableCell>
              <TableCell>{row.player2}</TableCell>
              <TableCell align="right">{row.distance}</TableCell>
              <TableCell align="right">{role === 'batter' ? row.player1_innings : row.player1_balls}</TableCell>
              <TableCell align="right">{role === 'batter' ? row.player2_innings : row.player2_balls}</TableCell>
            </TableRow>
          ))}
          {rows.length === 0 && (
            <TableRow>
              <TableCell colSpan={6} align="center">No results</TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </TableContainer>
  </Box>
);

const RoleSection = ({ title, board }) => {
  if (!board) return null;
  return (
    <Card variant="outlined">
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2, flexWrap: 'wrap' }}>
          <Typography variant="h5">{title}</Typography>
          <Chip size="small" label={`${board.qualified_players || 0} qualified`} />
          {board.warning && <Chip size="small" color="warning" variant="outlined" label={board.warning} />}
        </Box>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <PairTable title="Most Similar" rows={board.most_similar} role={board.role} />
          </Grid>
          <Grid item xs={12} md={6}>
            <PairTable title="Most Dissimilar" rows={board.most_dissimilar} role={board.role} />
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
};

const DoppelgangerLeaderboard = () => {
  const [startDate, setStartDate] = useState(DEFAULT_START);
  const [endDate, setEndDate] = useState(TODAY);
  const [minBattingInnings, setMinBattingInnings] = useState(25);
  const [minBowlingBalls, setMinBowlingBalls] = useState(240);
  const [topPairs, setTopPairs] = useState(10);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);

  const filterSummary = useMemo(() => ([
    'Top 5 leagues: IPL, BBL, PSL, CPL, SA20',
    'Top 10 international teams only',
  ]), []);

  const fetchLeaderboard = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        start_date: startDate,
        end_date: endDate,
        min_batting_innings: String(minBattingInnings),
        min_bowling_balls: String(minBowlingBalls),
        top_n_pairs: String(topPairs),
      });
      const res = await axios.get(`${config.API_URL}/search/doppelgangers/leaderboard?${params.toString()}`);
      setData(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load doppelganger leaderboard');
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      <Typography variant="h4" sx={{ mb: 1, fontWeight: 700 }}>
        Doppelganger Leaderboard
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
        Global most similar and most dissimilar batter/bowler pairs for a selected timeframe.
      </Typography>

      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
        {filterSummary.map((label) => (
          <Chip key={label} label={label} size="small" variant="outlined" />
        ))}
      </Box>

      <Card variant="outlined" sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} md={2}>
              <TextField
                label="Start Date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                fullWidth
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <TextField
                label="End Date"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                fullWidth
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <TextField
                label="Min Batting Innings"
                type="number"
                value={minBattingInnings}
                onChange={(e) => setMinBattingInnings(Math.max(1, Number(e.target.value) || 1))}
                fullWidth
              />
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <TextField
                label="Min Bowling Balls"
                type="number"
                value={minBowlingBalls}
                onChange={(e) => setMinBowlingBalls(Math.max(1, Number(e.target.value) || 1))}
                fullWidth
              />
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <TextField
                label="Pairs"
                type="number"
                value={topPairs}
                onChange={(e) => setTopPairs(Math.max(1, Math.min(50, Number(e.target.value) || 1)))}
                fullWidth
              />
            </Grid>
            <Grid item xs={12} sm={6} md={2} sx={{ display: 'flex', alignItems: 'center' }}>
              <Button variant="contained" onClick={fetchLeaderboard} fullWidth disabled={loading}>
                {loading ? 'Loading...' : 'Run'}
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {!data && !loading && !error && (
        <Alert severity="info">Choose a timeframe and cutoffs, then run the leaderboard.</Alert>
      )}

      {data && (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          <RoleSection title="Batters" board={data.batters} />
          <RoleSection title="Bowlers" board={data.bowlers} />
        </Box>
      )}
    </Container>
  );
};

export default DoppelgangerLeaderboard;
