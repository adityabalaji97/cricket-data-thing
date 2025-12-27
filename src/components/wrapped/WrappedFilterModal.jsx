import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  FormGroup,
  FormControlLabel,
  Checkbox,
  TextField,
  Typography,
  Box,
  IconButton
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';

const AVAILABLE_LEAGUES = [
  { id: 'IPL', label: 'Indian Premier League', values: ['Indian Premier League', 'IPL'] },
  { id: 'BBL', label: 'Big Bash League', values: ['Big Bash League', 'BBL'] },
  { id: 'PSL', label: 'Pakistan Super League', values: ['Pakistan Super League', 'PSL'] },
  { id: 'SA20', label: 'SA20', values: ['SA20'] },
  { id: 'BLAST', label: 'Vitality Blast', values: ['Vitality Blast', 'T20 Blast'] },
  { id: 'SMASH', label: 'Super Smash', values: ['Super Smash'] },
];

// Convert selected league IDs to API values
const leagueIdsToValues = (selectedIds) => {
  return AVAILABLE_LEAGUES
    .filter(league => selectedIds.includes(league.id))
    .flatMap(league => league.values);
};

const WrappedFilterModal = ({ open, onClose, onApply, currentFilters }) => {
  const [startDate, setStartDate] = useState(currentFilters?.startDate || '2025-01-01');
  const [endDate, setEndDate] = useState(currentFilters?.endDate || '2025-12-31');
  const [selectedLeagues, setSelectedLeagues] = useState(
    currentFilters?.leagues || ['IPL', 'BBL', 'PSL', 'SA20', 'BLAST', 'SMASH']
  );
  const [includeInternational, setIncludeInternational] = useState(
    currentFilters?.includeInternational ?? true
  );

  const handleLeagueToggle = (leagueId) => {
    setSelectedLeagues(prev => 
      prev.includes(leagueId)
        ? prev.filter(id => id !== leagueId)
        : [...prev, leagueId]
    );
  };

  const handleApply = () => {
    onApply({
      startDate,
      endDate,
      leagues: selectedLeagues,  // Keep IDs for UI state
      leagueValues: leagueIdsToValues(selectedLeagues),  // Convert to API values
      includeInternational
    });
    onClose();
  };

  const handleReset = () => {
    setStartDate('2025-01-01');
    setEndDate('2025-12-31');
    setSelectedLeagues(['IPL', 'BBL', 'PSL', 'SA20', 'BLAST', 'SMASH']);
    setIncludeInternational(true);
  };

  return (
    <Dialog 
      open={open} 
      onClose={onClose}
      PaperProps={{
        sx: {
          bgcolor: '#1a1a1a',
          color: '#fff',
          borderRadius: 2,
          minWidth: 300,
          maxWidth: 400
        }
      }}
    >
      <DialogTitle sx={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        pb: 1
      }}>
        <Typography variant="h6">Filters</Typography>
        <IconButton onClick={onClose} size="small" sx={{ color: '#fff' }}>
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      
      <DialogContent sx={{ pt: 1 }}>
        {/* Date Range */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" sx={{ color: '#b3b3b3', mb: 1 }}>
            Date Range
          </Typography>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <TextField
              type="date"
              label="Start"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              size="small"
              InputLabelProps={{ shrink: true }}
              sx={{
                flex: 1,
                '& .MuiOutlinedInput-root': {
                  color: '#fff',
                  '& fieldset': { borderColor: '#444' },
                  '&:hover fieldset': { borderColor: '#666' },
                },
                '& .MuiInputLabel-root': { color: '#888' }
              }}
            />
            <TextField
              type="date"
              label="End"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              size="small"
              InputLabelProps={{ shrink: true }}
              sx={{
                flex: 1,
                '& .MuiOutlinedInput-root': {
                  color: '#fff',
                  '& fieldset': { borderColor: '#444' },
                  '&:hover fieldset': { borderColor: '#666' },
                },
                '& .MuiInputLabel-root': { color: '#888' }
              }}
            />
          </Box>
        </Box>

        {/* Competitions */}
        <Box sx={{ mb: 2 }}>
          <Typography variant="subtitle2" sx={{ color: '#b3b3b3', mb: 1 }}>
            Competitions
          </Typography>
          <FormGroup>
            <FormControlLabel
              control={
                <Checkbox 
                  checked={includeInternational}
                  onChange={(e) => setIncludeInternational(e.target.checked)}
                  sx={{ 
                    color: '#666',
                    '&.Mui-checked': { color: '#1DB954' }
                  }}
                />
              }
              label={<Typography sx={{ fontSize: '0.9rem' }}>T20 Internationals (Top 20 teams)</Typography>}
            />
            {AVAILABLE_LEAGUES.map(league => (
              <FormControlLabel
                key={league.id}
                control={
                  <Checkbox 
                    checked={selectedLeagues.includes(league.id)}
                    onChange={() => handleLeagueToggle(league.id)}
                    sx={{ 
                      color: '#666',
                      '&.Mui-checked': { color: '#1DB954' }
                    }}
                  />
                }
                label={<Typography sx={{ fontSize: '0.9rem' }}>{league.label}</Typography>}
              />
            ))}
          </FormGroup>
        </Box>
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2, justifyContent: 'space-between' }}>
        <Button 
          onClick={handleReset}
          sx={{ color: '#b3b3b3' }}
        >
          Reset
        </Button>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button onClick={onClose} sx={{ color: '#b3b3b3' }}>
            Cancel
          </Button>
          <Button 
            onClick={handleApply}
            variant="contained"
            sx={{ 
              bgcolor: '#1DB954',
              '&:hover': { bgcolor: '#1ed760' }
            }}
          >
            Apply
          </Button>
        </Box>
      </DialogActions>
    </Dialog>
  );
};

export default WrappedFilterModal;
