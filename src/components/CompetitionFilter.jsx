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

const buildAllLeaguesOption = () => ({ label: 'All Leagues', value: 'all' });

const CompetitionFilter = ({ onFilterChange, isMobile, value }) => {
    const [includeInternational, setIncludeInternational] = useState(value?.international ?? false);
    const [topTeams, setTopTeams] = useState(value?.topTeams ?? 10);
    const [selectedLeagues, setSelectedLeagues] = useState([buildAllLeaguesOption()]);
    const [leagues, setLeagues] = useState([]); 
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchCompetitions = async () => {
            try {
                setLoading(true);
                const response = await axios.get(`${config.API_URL}/competitions`);
                setLeagues(response.data.leagues);
            } catch (error) {
                setError('Failed to load competitions');
            } finally {
                setLoading(false);
            }
        };
        fetchCompetitions();
    }, []);

    useEffect(() => {
        if (!leagues.length) return;

        const resolvedFilters = value?.leagues?.length
            ? value
            : {
                leagues: leagues.map((league) => league.value),
                international: value?.international ?? false,
                topTeams: value?.topTeams ?? 10,
            };

        const allLeagueValues = leagues.map((league) => league.value);
        const includesAll =
            resolvedFilters.leagues.length === allLeagueValues.length &&
            resolvedFilters.leagues.every((league) => allLeagueValues.includes(league));

        const optionsByValue = new Map(leagues.map((league) => [league.value, league]));
        const nextSelectedLeagues = includesAll
            ? [buildAllLeaguesOption()]
            : resolvedFilters.leagues
                  .map((league) => optionsByValue.get(league))
                  .filter(Boolean);

        setSelectedLeagues(nextSelectedLeagues);
        setIncludeInternational(resolvedFilters.international);
        setTopTeams(resolvedFilters.topTeams);

        if (!value?.leagues?.length) {
            onFilterChange(resolvedFilters);
        }
    }, [leagues, value, onFilterChange]);

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
