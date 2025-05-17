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

const CompetitionFilter = ({ onFilterChange }) => {
    const [includeInternational, setIncludeInternational] = useState(false);
    const [topTeams, setTopTeams] = useState(10);
    const [selectedLeagues, setSelectedLeagues] = useState([]);
    const [leagues, setLeagues] = useState([]); 
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchCompetitions = async () => {
            try {
                setLoading(true);
                const response = await axios.get(`${config.API_URL}/competitions`);
                setLeagues(response.data.leagues);
                // Set initial state with empty leagues
                onFilterChange({
                    leagues: [],
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
            <FormGroup row>
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
                    sx={{ width: 400, mr: 2 }}
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
                        sx={{ width: 100 }}
                    />
                )}
            </FormGroup>
        </Box>
    );
};

export default CompetitionFilter;