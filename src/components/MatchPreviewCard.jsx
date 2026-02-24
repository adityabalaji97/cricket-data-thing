import React, { useEffect, useMemo, useState } from 'react';
import {
  Box,
  CircularProgress,
  Chip,
  Stack,
  Typography,
} from '@mui/material';
import axios from 'axios';
import config from '../config';

const MatchPreviewCard = ({
  venue,
  team1Identifier,
  team2Identifier,
  startDate,
  endDate,
  includeInternational = true,
  topTeams = 20,
  isMobile = false,
}) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const requestKey = useMemo(
    () => JSON.stringify({
      venue,
      team1Identifier,
      team2Identifier,
      startDate: startDate || null,
      endDate: endDate || null,
      includeInternational,
      topTeams,
    }),
    [venue, team1Identifier, team2Identifier, startDate, endDate, includeInternational, topTeams]
  );

  const parsedPreview = useMemo(() => {
    if (Array.isArray(data?.sections) && data.sections.length > 0) {
      return data.sections.map((s) => ({
        title: s.title,
        bullets: Array.isArray(s.bullets) ? s.bullets : [],
        paragraphs: [],
      }));
    }
    if (!data?.preview) return [];
    const lines = String(data.preview).split('\n');
    const sections = [];
    let current = null;

    lines.forEach((rawLine) => {
      const line = rawLine.trim();
      if (!line) return;
      if (line.startsWith('## ')) {
        if (current) sections.push(current);
        current = { title: line.replace(/^##\s+/, ''), bullets: [], paragraphs: [] };
        return;
      }
      if (!current) {
        current = { title: 'Preview', bullets: [], paragraphs: [] };
      }
      if (line.startsWith('- ')) {
        current.bullets.push(line.replace(/^- /, ''));
      } else {
        current.paragraphs.push(line);
      }
    });

    if (current) sections.push(current);
    return sections;
  }, [data?.preview, data?.sections]);

  useEffect(() => {
    if (!venue || !team1Identifier || !team2Identifier) return;
    let cancelled = false;

    const fetchPreview = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await axios.get(
          `${config.API_URL}/match-preview/${encodeURIComponent(venue)}/${encodeURIComponent(team1Identifier)}/${encodeURIComponent(team2Identifier)}`,
          {
            params: {
              ...(startDate ? { start_date: startDate } : {}),
              ...(endDate ? { end_date: endDate } : {}),
              include_international: includeInternational,
              top_teams: topTeams,
            }
          }
        );
        if (!cancelled) {
          setData(response.data);
        }
      } catch (err) {
        console.error('Error fetching match preview:', err);
        if (!cancelled) setError('Failed to load match preview');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchPreview();
    return () => {
      cancelled = true;
    };
  }, [requestKey, venue, team1Identifier, team2Identifier, startDate, endDate, includeInternational, topTeams]);

  if (!venue || !team1Identifier || !team2Identifier) return null;

  if (loading && !data) {
    return (
      <Box sx={{ p: 2, borderRadius: 2, bgcolor: 'rgba(25,118,210,0.04)', border: '1px solid rgba(25,118,210,0.15)' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <CircularProgress size={18} />
          <Typography variant="body2">Generating AI preview...</Typography>
        </Box>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 2, borderRadius: 2, bgcolor: 'rgba(244,67,54,0.04)', border: '1px solid rgba(244,67,54,0.15)' }}>
        <Typography variant="body2" color="error">{error}</Typography>
      </Box>
    );
  }

  if (!data?.preview) return null;

  return (
    <Box sx={{ p: { xs: 1.5, sm: 2 }, borderRadius: 2, bgcolor: 'rgba(0,0,0,0.02)', border: '1px solid rgba(0,0,0,0.08)' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 1, alignItems: 'center', mb: 1, flexWrap: 'wrap' }}>
        <Typography variant={isMobile ? 'subtitle1' : 'h6'}>
          AI Match Preview
        </Typography>
        <Stack direction="row" spacing={0.5} alignItems="center">
          {data?.preview_mode && (
            <Chip size="small" label={data.preview_mode} variant="outlined" />
          )}
          {data.cached && (
            <Chip size="small" label="cached" variant="outlined" />
          )}
        </Stack>
      </Box>
      <Box>
        {(parsedPreview.length ? parsedPreview : [{ title: 'Preview', bullets: [], paragraphs: [String(data.preview)] }]).map((section) => (
          <Box key={section.title} sx={{ mb: 1.2 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.4 }}>
              {section.title}
            </Typography>
            {section.bullets.map((bullet, idx) => (
              <Typography key={`${section.title}-b-${idx}`} variant="body2" sx={{ lineHeight: 1.35, mb: 0.2 }}>
                • {bullet}
              </Typography>
            ))}
            {section.paragraphs.map((paragraph, idx) => (
              <Typography key={`${section.title}-p-${idx}`} variant="body2" sx={{ lineHeight: 1.35, mb: 0.2 }}>
                {paragraph}
              </Typography>
            ))}
          </Box>
        ))}
      </Box>
    </Box>
  );
};

export default MatchPreviewCard;
