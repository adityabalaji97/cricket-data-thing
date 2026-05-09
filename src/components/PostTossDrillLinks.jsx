import React, { useState } from 'react';
import axios from 'axios';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  CircularProgress,
  Alert,
  Stack,
  IconButton,
  Tooltip,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import config from '../config';

const PostTossDrillLinks = ({ links, venue, battingFirstTeam, battingSecondTeam, isMobile }) => {
  const [summaries, setSummaries] = useState({});
  const [batchLoading, setBatchLoading] = useState(false);
  const [batchError, setBatchError] = useState(null);
  const [expandedKeys, setExpandedKeys] = useState(new Set());

  if (!links || links.length === 0) return null;

  const handleAccordionToggle = (key) => {
    setExpandedKeys(prev => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const handleSummarizeAll = async () => {
    setBatchLoading(true);
    setBatchError(null);
    try {
      const items = links.map(link => ({
        key: link.key,
        context_description: link.description,
        filters: link.filters,
        group_by: link.group_by,
      }));
      const response = await axios.post(`${config.API_URL}/summarize/batch`, { items });
      const data = response.data;
      if (data.success) {
        const nextSummaries = {};
        Object.entries(data.summaries).forEach(([key, result]) => {
          nextSummaries[key] = {
            summary: result.summary,
            error: result.error || null,
            resultCount: result.result_count,
          };
        });
        setSummaries(nextSummaries);
        setExpandedKeys(new Set(links.map(l => l.key)));
      } else {
        setBatchError('Failed to generate summaries');
      }
    } catch (err) {
      setBatchError(err.response?.data?.detail || err.message || 'Failed to generate summaries');
    } finally {
      setBatchLoading(false);
    }
  };

  const hasSummaries = Object.keys(summaries).length > 0;

  return (
    <Card variant="outlined" sx={{ mb: 2 }}>
      <CardContent sx={{ pb: '16px !important' }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
          <Typography variant="subtitle1" fontWeight={600}>
            Venue Deep-Dive
          </Typography>
          <Button
            variant={hasSummaries ? 'outlined' : 'contained'}
            size="small"
            startIcon={batchLoading ? <CircularProgress size={16} /> : <AutoAwesomeIcon />}
            onClick={handleSummarizeAll}
            disabled={batchLoading}
          >
            {batchLoading ? 'Analyzing...' : hasSummaries ? 'Re-analyze' : 'Summarize All'}
          </Button>
        </Stack>

        {batchError && (
          <Alert severity="error" sx={{ mb: 1 }} onClose={() => setBatchError(null)}>
            {batchError}
          </Alert>
        )}

        {links.map((link) => {
          const s = summaries[link.key];
          return (
            <Accordion
              key={link.key}
              expanded={expandedKeys.has(link.key)}
              onChange={() => handleAccordionToggle(link.key)}
              disableGutters
              sx={{
                '&:before': { display: 'none' },
                boxShadow: 'none',
                border: '1px solid',
                borderColor: 'divider',
                '&:not(:last-child)': { mb: 0.5 },
              }}
            >
              <AccordionSummary
                expandIcon={<ExpandMoreIcon />}
                sx={{ minHeight: 40, '& .MuiAccordionSummary-content': { my: 0.5, alignItems: 'center' } }}
              >
                <Stack direction="row" alignItems="center" spacing={1} sx={{ flex: 1, mr: 1 }}>
                  <Typography variant="body2" sx={{ flex: 1 }}>
                    {link.description}
                  </Typography>
                  {s && s.resultCount > 0 && (
                    <Typography variant="caption" color="text.secondary">
                      {s.resultCount} rows
                    </Typography>
                  )}
                  <Tooltip title="Open in Query Builder">
                    <IconButton
                      size="small"
                      href={link.url}
                      target="_blank"
                      rel="noopener"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <OpenInNewIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </Stack>
              </AccordionSummary>
              <AccordionDetails sx={{ pt: 0, pb: 1.5 }}>
                {batchLoading ? (
                  <Stack direction="row" alignItems="center" spacing={1}>
                    <CircularProgress size={14} />
                    <Typography variant="body2" color="text.secondary">Analyzing...</Typography>
                  </Stack>
                ) : s ? (
                  s.error ? (
                    <Alert severity="warning" sx={{ py: 0 }}>{s.error}</Alert>
                  ) : s.resultCount === 0 ? (
                    <Typography variant="body2" color="text.secondary">
                      No venue data found for this query.
                    </Typography>
                  ) : (
                    <Typography
                      variant="body2"
                      sx={{ whiteSpace: 'pre-line', lineHeight: 1.6 }}
                    >
                      {s.summary}
                    </Typography>
                  )
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    Click "Summarize All" to generate AI insights for this query.
                  </Typography>
                )}
              </AccordionDetails>
            </Accordion>
          );
        })}
      </CardContent>
    </Card>
  );
};

export default PostTossDrillLinks;
