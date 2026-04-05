import React, { useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Collapse,
  Divider,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';

const displayNumber = (value, digits = 2) => (
  value === null || value === undefined || Number.isNaN(Number(value))
    ? '-'
    : Number(value).toFixed(digits)
);

const DetailTable = ({ section }) => {
  const metricEntries = Object.entries(section || {}).filter(([key]) => key !== 'innings_count');
  if (!metricEntries.length) {
    return null;
  }

  return (
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell>Metric</TableCell>
          <TableCell align="right">Value</TableCell>
          <TableCell align="right">Percentile</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {metricEntries.map(([metricKey, metric]) => (
          <TableRow key={metricKey}>
            <TableCell sx={{ textTransform: 'capitalize' }}>{metricKey.replace(/_/g, ' ')}</TableCell>
            <TableCell align="right">{displayNumber(metric?.value)}</TableCell>
            <TableCell align="right">{displayNumber(metric?.percentile, 1)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
};

const InningsBlock = ({ title, inningsData, expanded }) => {
  const batting = inningsData?.batting || {};
  const bowling = inningsData?.bowling || {};

  return (
    <Card variant="outlined">
      <CardContent sx={{ py: 1.5 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
          {title}
        </Typography>
        <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ rowGap: 1 }}>
          <Chip size="small" variant="outlined" label={`Bat SR P${displayNumber(batting?.strike_rate?.percentile, 1)}`} />
          <Chip size="small" variant="outlined" label={`Bat Avg P${displayNumber(batting?.avg_runs?.percentile, 1)}`} />
          <Chip size="small" variant="outlined" label={`Bowl Econ P${displayNumber(bowling?.economy?.percentile, 1)}`} />
          <Chip size="small" variant="outlined" label={`Bowl Wkts P${displayNumber(bowling?.wickets_per_innings?.percentile, 1)}`} />
        </Stack>

        <Collapse in={expanded}>
          <Divider sx={{ my: 1.25 }} />
          <Typography variant="caption" color="text.secondary">
            Batting (innings: {batting?.innings_count ?? 0})
          </Typography>
          <DetailTable section={batting} />
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
            Bowling (innings: {bowling?.innings_count ?? 0})
          </Typography>
          <DetailTable section={bowling} />
        </Collapse>
      </CardContent>
    </Card>
  );
};

const TeamRelativeMetricsSection = ({
  data,
  loading,
  error,
  onRetry,
  isMobile = false,
}) => {
  const [expanded, setExpanded] = useState(false);

  const hasPayload = useMemo(
    () => Boolean(data?.innings_1 || data?.innings_2),
    [data],
  );

  if (loading && !hasPayload) {
    return (
      <Box sx={{ py: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
        <CircularProgress size={18} />
        <Typography variant="body2">Loading relative metrics…</Typography>
      </Box>
    );
  }

  if (error && !hasPayload) {
    return (
      <Alert
        severity="error"
        action={onRetry ? <Button color="inherit" size="small" onClick={onRetry}>Retry</Button> : null}
      >
        {error}
      </Alert>
    );
  }

  if (!hasPayload) {
    return (
      <Alert severity="info">
        Relative metrics are unavailable for the selected filters.
      </Alert>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
      {data?.data_quality_note && (
        <Alert severity="info">{data.data_quality_note}</Alert>
      )}

      <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" sx={{ rowGap: 1 }}>
        <Chip size="small" variant="outlined" label={`Benchmark: ${data?.benchmark_window_matches ?? 10} matches`} />
        {data?.effective_start_date && (
          <Chip size="small" variant="outlined" label={`Effective start: ${data.effective_start_date}`} />
        )}
        <Button size="small" onClick={() => setExpanded((prev) => !prev)}>
          {expanded ? 'Hide details' : 'Show details'}
        </Button>
      </Stack>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(2, minmax(0, 1fr))' }, gap: 1.5 }}>
        <InningsBlock title="Innings 1" inningsData={data?.innings_1} expanded={expanded} />
        <InningsBlock title="Innings 2" inningsData={data?.innings_2} expanded={expanded} />
      </Box>

      {error && (
        <Alert severity="warning" sx={{ mt: isMobile ? 0.5 : 0 }}>
          {error}
        </Alert>
      )}
    </Box>
  );
};

export default TeamRelativeMetricsSection;
