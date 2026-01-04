import React, { useState } from 'react';
import { 
  Box, 
  Typography, 
  Button, 
  Chip, 
  Card, 
  CardContent,
  Collapse,
  IconButton
} from '@mui/material';
import { Link } from 'react-router-dom';
import SearchIcon from '@mui/icons-material/Search';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';

/**
 * ContextualQueryPrompts Component
 * 
 * Displays contextual Query Builder links based on the current page context.
 * Converts casual browsers into power users by showing interesting questions they can explore.
 * 
 * @param {Array} queries - Array of query objects from queryBuilderLinks.js
 * @param {string} title - Section title (optional, default: "🔍 Explore in Query Builder")
 * @param {number} initialCount - Number of queries to show initially (default: 3)
 * @param {boolean} compact - Use compact styling for inline placement (default: false)
 */
const ContextualQueryPrompts = ({ 
  queries = [], 
  title = "🔍 Explore in Query Builder",
  initialCount = 3,
  compact = false 
}) => {
  const [expanded, setExpanded] = useState(false);
  
  // Early return if no queries
  if (!queries || queries.length === 0) {
    return null;
  }
  
  // Sort by priority and slice for display
  const sortedQueries = [...queries].sort((a, b) => a.priority - b.priority);
  const visibleQueries = expanded ? sortedQueries : sortedQueries.slice(0, initialCount);
  const hasMore = sortedQueries.length > initialCount;
  
  // Render compact version for embedding in stat cards
  if (compact) {
    return (
      <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid', borderColor: 'divider' }}>
        <Typography 
          variant="caption" 
          color="text.secondary" 
          sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}
        >
          <SearchIcon sx={{ fontSize: 14 }} />
          Dig Deeper
        </Typography>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
          {visibleQueries.map((query, index) => (
            <Chip
              key={index}
              label={query.question}
              component={Link}
              to={query.url}
              clickable
              size="small"
              variant="outlined"
              color="primary"
              sx={{ 
                fontSize: '0.7rem',
                minHeight: 44,
                '& .MuiChip-label': {
                  px: 1.5,
                },
                '&:focus-visible': {
                  outline: '2px solid',
                  outlineColor: 'primary.main',
                  outlineOffset: 2,
                },
                '&:hover': { 
                  backgroundColor: 'primary.light',
                  color: 'white'
                }
              }}
            />
          ))}
        </Box>
      </Box>
    );
  }
  
  // Full card version (default)
  return (
    <Card sx={{ mt: 3, mb: 3, backgroundColor: 'grey.50' }}>
      <CardContent>
        {/* Header with title and expand/collapse button */}
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <TrendingUpIcon color="primary" />
            {title}
          </Typography>
          {hasMore && (
            <IconButton
              size="medium"
              onClick={() => setExpanded(!expanded)}
              sx={{
                minWidth: 44,
                minHeight: 44,
                '&:focus-visible': {
                  outline: '2px solid',
                  outlineColor: 'primary.main',
                  outlineOffset: 2,
                },
              }}
            >
              {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          )}
        </Box>
        
        {/* Subtitle */}
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Click any question below to see the data in Query Builder:
        </Typography>
        
        {/* Query list */}
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
          {visibleQueries.map((query, index) => (
            <Box
              key={index}
              component={Link}
              to={query.url}
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 1,
                p: 1.5,
                minHeight: 44,
                borderRadius: 1,
                backgroundColor: 'white',
                textDecoration: 'none',
                color: 'inherit',
                border: '1px solid',
                borderColor: 'grey.200',
                transition: 'all 0.2s',
                '&:hover': {
                  borderColor: 'primary.main',
                  backgroundColor: 'primary.50',
                  transform: 'translateX(4px)',
                },
                '&:focus-visible': {
                  outline: '2px solid',
                  outlineColor: 'primary.main',
                  outlineOffset: 2,
                },
              }}
            >
              <SearchIcon color="primary" sx={{ fontSize: 20 }} />
              <Typography variant="body2" sx={{ flex: 1, fontWeight: 500 }}>
                {query.question}
              </Typography>
              <Box sx={{ display: 'flex', gap: 0.5 }}>
                {query.tags.slice(0, 2).map((tag, tagIndex) => (
                  <Chip
                    key={tagIndex}
                    label={tag}
                    size="small"
                    variant="outlined"
                    sx={{ fontSize: '0.65rem', height: 20 }}
                  />
                ))}
              </Box>
            </Box>
          ))}
        </Box>
        
        {/* Show more button */}
        {hasMore && (
          <Collapse in={!expanded}>
            <Button
              fullWidth
              variant="text"
              onClick={() => setExpanded(true)}
              sx={{
                mt: 1,
                minHeight: 44,
                '&:focus-visible': {
                  outline: '2px solid',
                  outlineColor: 'primary.main',
                  outlineOffset: 2,
                },
              }}
            >
              Show {sortedQueries.length - initialCount} more queries
            </Button>
          </Collapse>
        )}
      </CardContent>
    </Card>
  );
};

export default ContextualQueryPrompts;
