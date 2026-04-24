import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  Collapse,
  Divider,
  IconButton,
  Paper,
  Tooltip,
  Typography,
} from '@mui/material';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';

const CONFIDENCE_STYLE = {
  high: { label: 'High confidence', color: 'success' },
  medium: { label: 'Medium confidence', color: 'warning' },
  low: { label: 'Low confidence', color: 'error' },
};

const ENTITY_COLOR = {
  player: 'primary',
  team: 'success',
  filter: 'warning',
};

const normalizeConfidence = (confidence) => {
  const key = String(confidence || '').toLowerCase();
  if (key in CONFIDENCE_STYLE) {
    return key;
  }
  return 'medium';
};

const normalizeEntityType = (entityType) => {
  const normalized = String(entityType || '').toLowerCase();
  if (normalized === 'player' || normalized === 'team') {
    return normalized;
  }
  return 'filter';
};

const NLInterpretation = ({
  interpretation,
  confidence,
  rawFilters,
  onSuggestionClick,
  onClose,
  disabled = false,
}) => {
  const [showRawFilters, setShowRawFilters] = useState(false);
  const [collapsed, setCollapsed] = useState(true);

  useEffect(() => {
    setCollapsed(true);
    setShowRawFilters(false);
  }, [interpretation]);

  const parsedEntities = useMemo(() => {
    if (!Array.isArray(interpretation?.parsed_entities)) {
      return [];
    }
    return interpretation.parsed_entities.filter((entity) => entity && entity.value);
  }, [interpretation]);

  const suggestions = useMemo(() => {
    if (!Array.isArray(interpretation?.suggestions)) {
      return [];
    }
    return interpretation.suggestions.filter(Boolean);
  }, [interpretation]);

  const hasRawFilters = rawFilters && Object.keys(rawFilters).length > 0;
  const confidenceKey = normalizeConfidence(confidence);
  const confidenceMeta = CONFIDENCE_STYLE[confidenceKey];
  const summaryText = interpretation?.summary || 'Interpretation unavailable.';
  const headerText = `AI Interpretation \u00b7 ${confidenceMeta.label}`;

  return (
    <Paper elevation={1} sx={{ mb: 2, p: 2, border: 1, borderColor: 'divider' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 1.5 }}>
        <Box sx={{ minWidth: 0, flex: 1 }}>
          <Typography variant="subtitle2" sx={{ mb: 0.5, color: 'text.secondary' }}>
            {headerText}
          </Typography>
          {collapsed && (
            <Typography
              variant="body2"
              sx={{
                fontWeight: 500,
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}
            >
              {summaryText}
            </Typography>
          )}
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Chip
            size="small"
            color={confidenceMeta.color}
            label={confidenceMeta.label}
            sx={{ fontWeight: 600 }}
          />
          <IconButton
            size="small"
            onClick={() => setCollapsed((prev) => !prev)}
            aria-label={collapsed ? 'Expand interpretation' : 'Collapse interpretation'}
          >
            {collapsed ? <ExpandMoreIcon fontSize="small" /> : <ExpandLessIcon fontSize="small" />}
          </IconButton>
        </Box>
      </Box>

      <Collapse in={!collapsed}>
        <Box sx={{ mt: 1.25 }}>
          <Typography variant="body2" sx={{ fontWeight: 500 }}>
            {summaryText}
          </Typography>
        </Box>

        {parsedEntities.length > 0 && (
          <Box sx={{ mt: 1.75 }}>
            <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 0.75 }}>
              Parsed entities
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
              {parsedEntities.map((entity, index) => {
                const entityType = normalizeEntityType(entity.type);
                const chip = (
                  <Chip
                    key={`${entityType}-${entity.value}-${index}`}
                    size="small"
                    color={ENTITY_COLOR[entityType]}
                    label={entity.value}
                    variant="filled"
                  />
                );

                if (entity.matched_from) {
                  return (
                    <Tooltip key={`${entityType}-${entity.value}-${index}`} title={`Matched from: ${entity.matched_from}`}>
                      {chip}
                    </Tooltip>
                  );
                }

                return chip;
              })}
            </Box>
          </Box>
        )}

        {suggestions.length > 0 && (
          <>
            <Divider sx={{ my: 1.5 }} />
            <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 0.75 }}>
              Refinement suggestions
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
              {suggestions.map((suggestion, index) => (
                <Chip
                  key={`${suggestion}-${index}`}
                  size="small"
                  label={suggestion}
                  clickable={!!onSuggestionClick}
                  disabled={disabled}
                  onClick={() => onSuggestionClick?.(suggestion)}
                  variant="outlined"
                  sx={{ maxWidth: '100%' }}
                />
              ))}
            </Box>
          </>
        )}

        {hasRawFilters && (
          <Box sx={{ mt: 1.5 }}>
            <Button
              size="small"
              onClick={() => setShowRawFilters((prev) => !prev)}
              sx={{ px: 0, minWidth: 0 }}
            >
              {showRawFilters ? 'Hide raw filters' : 'Show raw filters'}
            </Button>

            {showRawFilters && (
              <Alert severity="info" sx={{ mt: 1 }}>
                <Box
                  component="pre"
                  sx={{
                    m: 0,
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    fontSize: 12,
                    lineHeight: 1.4,
                  }}
                >
                  {JSON.stringify(rawFilters, null, 2)}
                </Box>
              </Alert>
            )}
          </Box>
        )}

        {onClose && (
          <Box sx={{ mt: 1.5 }}>
            <Button size="small" onClick={onClose} sx={{ px: 0, minWidth: 0 }}>
              Dismiss interpretation
            </Button>
          </Box>
        )}
      </Collapse>
    </Paper>
  );
};

export default NLInterpretation;
