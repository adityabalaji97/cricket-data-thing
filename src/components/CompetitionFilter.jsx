import React, { useState, useEffect } from 'react';
import { 
  Box, 
  TextField, 
  Autocomplete, 
  FormGroup,
  FormControlLabel,
  Checkbox,
  CircularProgress,
  Alert 
} from '@mui/material';
import axios from 'axios';
import config from '../config';

const CompetitionFilter = ({ onFilterChange, isMobile }) => {
    const [includeInternational, setIncludeInternational] = useState(false);
    const [topTeams, setTopTeams] = useState(10);
    const [selectedLeagues, setSelectedLeagues] = useState([{ label: 'All Leagues', value: 'all' }]);
    const [leagues, setLeagues] = useState([]); 
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchCompetitions = async () => {
            try {
                setLoading(true);
                const response = await axios.get(`${config.API_URL}/competitions`);
                setLeagues(response.data.leagues);
                // Set initial state with all leagues
                onFilterChange({
                    leagues: response.data.leagues.map(league => league.value),
                    international: false,
                    topTeams: 10
                });
            } catch (error) {
                setError('Failed to load competitions');
            } finally {
                setLoading(false);
            }
        };
        fetchCompetitions();
    }, []);

    // Handle selection changes including "All Leagues"
    const handleSelectionChange = (newLeagues, newInternational, newTopTeams) => {
        // Check if "All Leagues" is selected
        const hasAllLeagues = newLeagues?.some(league => league.value === 'all');
        
        // If "All Leagues" is selected, include all available leagues
        const leaguesToSend = hasAllLeagues 
            ? leagues.map(league => league.value)
            : (newLeagues?.map(league => league.value) || []);

        onFilterChange({
            leagues: leaguesToSend,
            international: newInternational,
            topTeams: newTopTeams
        });
    };

    // Handle Autocomplete change
    const handleAutocompleteChange = (event, newValue) => {
        // Check if "All Leagues" is being selected
        const isAllLeaguesSelected = newValue?.some(league => league.value === 'all');
        
        // If "All Leagues" is selected, include all leagues
        const updatedSelection = isAllLeaguesSelected 
            ? [{ label: 'All Leagues', value: 'all' }]
            : newValue;

        setSelectedLeagues(updatedSelection);
        handleSelectionChange(updatedSelection, includeInternational, topTeams);
    };

    if (loading) return <CircularProgress size={20} />;
    if (error) return <Alert severity="error">{error}</Alert>;

    return (
        <Box sx={{ mb: 2 }}>
            <FormGroup sx={{ flexDirection: isMobile ? 'column' : 'row', gap: 2, alignItems: 'flex-start' }}>
                <Autocomplete
                    multiple
                    value={selectedLeagues}
                    onChange={handleAutocompleteChange}
                    options={[
                        {
                            label: 'All Leagues',
                            value: 'all'
                        },
                        ...leagues
                    ]}
                    getOptionLabel={(option) => option.label}
                    isOptionEqualToValue={(option, value) => option.value === value.value}
                    renderInput={(params) => (
                        <TextField {...params} label="Select Leagues" />
                    )}
                    sx={{ width: isMobile ? '100%' : 400, mb: isMobile ? 1 : 0, mr: isMobile ? 0 : 2 }}
                />
                <FormControlLabel
                    control={
                        <Checkbox
                            checked={includeInternational}
                            onChange={(e) => {
                                const newValue = e.target.checked;
                                setIncludeInternational(newValue);
                                handleSelectionChange(selectedLeagues, newValue, topTeams);
                            }}
                        />
                    }
                    label="Include International Matches"
                />
                {includeInternational && (
                    <Box sx={{ display: 'flex', alignItems: 'center', width: isMobile ? '100%' : 'auto', mt: isMobile ? 1 : 0 }}>
                        <TextField
                            type="number"
                            label="Top Teams"
                            value={topTeams}
                            onChange={(e) => {
                                const newValue = parseInt(e.target.value);
                                setTopTeams(newValue);
                                handleSelectionChange(selectedLeagues, includeInternational, newValue);
                            }}
                            inputProps={{ min: 1, max: 20 }}
                            sx={{ width: isMobile ? '100%' : 100 }}
                            fullWidth={isMobile}
                        />
                    </Box>
                )}
            </FormGroup>
        </Box>
    );
};

export default CompetitionFilter;