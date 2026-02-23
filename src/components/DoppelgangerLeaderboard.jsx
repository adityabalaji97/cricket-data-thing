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
  MenuItem,
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
import {
  Legend,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import config from '../config';

const TODAY = new Date().toISOString().split('T')[0];
const DEFAULT_START = `${new Date().getFullYear() - 1}-01-01`;

const PairRadar = ({ pair, radarMap }) => {
  if (!pair || !radarMap) return null;
  const p1 = radarMap[pair.player1];
  const p2 = radarMap[pair.player2];
  if (!p1 || !p2) return null;

  const p2ByKey = new Map(p2.map((m) => [m.key, m]));
  const chartData = p1
    .map((m1) => {
      const m2 = p2ByKey.get(m1.key);
      if (!m2) return null;
      return {
        metric: m1.metric,
        p1Pct: m1.percentile,
        p2Pct: m2.percentile,
        p1Raw: m1.raw_value,
        p2Raw: m2.raw_value,
        avg: m1.league_avg,
      };
    })
    .filter(Boolean);

  if (!chartData.length) return null;

  return (
    <Box sx={{ mt: 2 }}>
      <Typography variant="body2" sx={{ mb: 1, fontWeight: 600 }}>
        Radar: {pair.player1} vs {pair.player2}
      </Typography>
      <Box sx={{ width: '100%', height: 380 }}>
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={chartData} outerRadius="68%">
            <PolarGrid />
            <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11 }} />
            <PolarRadiusAxis domain={[0, 100]} tickCount={6} tick={{ fontSize: 10 }} />
            <Radar name={pair.player1} dataKey="p1Pct" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.2} />
            <Radar name={pair.player2} dataKey="p2Pct" stroke="#f97316" fill="#f97316" fillOpacity={0.2} />
            <Tooltip
              labelFormatter={(label, payload) => {
                const row = payload?.[0]?.payload;
                return row ? `${label} (league avg ${row.avg})` : label;
              }}
              formatter={(value, name, ctx) => {
                const row = ctx?.payload || {};
                if (name === pair.player1) return [`${value}% (raw ${row.p1Raw})`, pair.player1];
                if (name === pair.player2) return [`${value}% (raw ${row.p2Raw})`, pair.player2];
                return [value, name];
              }}
            />
            <Legend />
          </RadarChart>
        </ResponsiveContainer>
      </Box>
    </Box>
  );
};

const PairTable = ({ title, rows = [], role, selectedKey, onSelect }) => (
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
          {rows.map((row, idx) => {
            const rowKey = `${row.player1}|${row.player2}|${row.distance}`;
            return (
            <TableRow
              key={`${row.player1}-${row.player2}-${idx}`}
              hover
              selected={rowKey === selectedKey}
              onClick={() => onSelect?.(row)}
              sx={{ cursor: onSelect ? 'pointer' : 'default' }}
            >
              <TableCell>{idx + 1}</TableCell>
              <TableCell>{row.player1}</TableCell>
              <TableCell>{row.player2}</TableCell>
              <TableCell align="right">{row.distance}</TableCell>
              <TableCell align="right">{role === 'batter' ? row.player1_innings : row.player1_balls}</TableCell>
              <TableCell align="right">{role === 'batter' ? row.player2_innings : row.player2_balls}</TableCell>
            </TableRow>
          )})}
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

const RoleSection = ({ title, board, batterMetricHelp }) => {
  const [selectedPair, setSelectedPair] = useState(null);
  if (!board) return null;
  const selectedKey = selectedPair ? `${selectedPair.player1}|${selectedPair.player2}|${selectedPair.distance}` : null;
  return (
    <Card variant="outlined">
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2, flexWrap: 'wrap' }}>
          <Typography variant="h5">{title}</Typography>
          <Chip size="small" label={`${board.qualified_players || 0} qualified`} />
          {board.warning && <Chip size="small" color="warning" variant="outlined" label={board.warning} />}
        </Box>
        {board.distance_explanation && (
          <Alert severity="info" sx={{ mb: 2 }}>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>Distance Meaning</Typography>
            <Typography variant="body2">{board.distance_explanation.summary}</Typography>
            {board.role === 'batter' && batterMetricHelp && (
              <Typography variant="body2" sx={{ mt: 0.5 }}>
                {batterMetricHelp}
              </Typography>
            )}
          </Alert>
        )}
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <PairTable
              title="Most Similar"
              rows={board.most_similar}
              role={board.role}
              selectedKey={selectedKey}
              onSelect={setSelectedPair}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <PairTable
              title="Most Dissimilar"
              rows={board.most_dissimilar}
              role={board.role}
              selectedKey={selectedKey}
              onSelect={setSelectedPair}
            />
          </Grid>
        </Grid>
        <PairRadar pair={selectedPair} radarMap={board.player_radar_metrics} />
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
  const [batterMetricLevel, setBatterMetricLevel] = useState('bowling_type');
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
        batter_metric_level: batterMetricLevel,
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
      <Alert severity="info" sx={{ mb: 2 }}>
        Click a pair row to open a radar chart. Distance is computed as Euclidean distance on z-score normalized feature vectors, so lower values mean closer profiles.
      </Alert>
      <Alert severity="info" sx={{ mb: 2 }}>
        Batter metric level controls how granular batter doppelganger matching is. For each selected level, only batters with all required data for that level are included.
      </Alert>

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
                label="Batter Metric Level"
                select
                value={batterMetricLevel}
                onChange={(e) => setBatterMetricLevel(e.target.value)}
                fullWidth
              >
                <MenuItem value="basic">Basic (core + phase)</MenuItem>
                <MenuItem value="pace_spin">Intermediate (core + phase + pace/spin)</MenuItem>
                <MenuItem value="bowling_type">Advanced (core + phase + pace/spin + bowling type)</MenuItem>
              </TextField>
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
          <RoleSection title="Batters" board={data.batters} batterMetricHelp={data?.batter_metric_levels?.availability_rule} />
          <RoleSection title="Bowlers" board={data.bowlers} />
        </Box>
      )}
    </Container>
  );
};

export default DoppelgangerLeaderboard;
