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
import { colors } from '../theme/designSystem';

const touchTargetStyles = {
    '& .MuiInputBase-root': {
        minHeight: 44,
    },
    '& .MuiOutlinedInput-notchedOutline': {
        borderColor: colors.neutral[300],
    },
    '&:hover .MuiOutlinedInput-notchedOutline': {
        borderColor: colors.primary[400],
    },
    '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
        borderColor: colors.primary[600],
        borderWidth: 2,
    },
};

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

        // When "All Leagues" is selected (empty array or all leagues), send empty array to backend
        // This prevents the URL from becoming too long with 50+ league parameters
        const allLeagueValues = leagues.map((league) => league.value);
        const isAllLeagues = !value?.leagues?.length ||
            (value.leagues.length === allLeagueValues.length &&
             value.leagues.every((league) => allLeagueValues.includes(league)));

        const resolvedFilters = {
            leagues: isAllLeagues ? [] : value.leagues,
            international: value?.international ?? false,
            topTeams: value?.topTeams ?? 10,
        };

        const optionsByValue = new Map(leagues.map((league) => [league.value, league]));
        const nextSelectedLeagues = isAllLeagues
            ? [buildAllLeaguesOption()]
            : resolvedFilters.leagues
                  .map((league) => optionsByValue.get(league))
                  .filter(Boolean);

        setSelectedLeagues(nextSelectedLeagues);
        setIncludeInternational(resolvedFilters.international);
        setTopTeams(resolvedFilters.topTeams);

        const leaguesEqual = Array.isArray(value?.leagues)
            && value.leagues.length === resolvedFilters.leagues.length
            && value.leagues.every((league) => resolvedFilters.leagues.includes(league));
        const internationalEqual = value?.international === resolvedFilters.international;
        const topTeamsEqual = value?.topTeams === resolvedFilters.topTeams;

        if (!leaguesEqual || !internationalEqual || !topTeamsEqual) {
            onFilterChange(resolvedFilters);
        }
    }, [leagues, value, onFilterChange]);

    // Handle selection changes including "All Leagues"
    const handleSelectionChange = (newLeagues, newInternational, newTopTeams) => {
        // Check if "All Leagues" is selected
        const hasAllLeagues = newLeagues?.some(league => league.value === 'all');

        // If "All Leagues" is selected, send empty array (backend interprets as all leagues)
        // This prevents the URL from becoming too long with 50+ league parameters
        const leaguesToSend = hasAllLeagues
            ? []
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
                    size="medium"
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
                        <TextField {...params} label="Select Leagues" sx={touchTargetStyles} />
                    )}
                    sx={{ width: isMobile ? '100%' : 400, mb: isMobile ? 1 : 0, mr: isMobile ? 0 : 2 }}
                />
                <FormControlLabel
                    sx={{ minHeight: 44 }}
                    control={
                        <Checkbox
                            checked={includeInternational}
                            onChange={(e) => {
                                const newValue = e.target.checked;
                                setIncludeInternational(newValue);
                                handleSelectionChange(selectedLeagues, newValue, topTeams);
                            }}
                            sx={{
                                p: 1.5,
                                '&:focus-visible': {
                                    outline: `2px solid ${colors.primary[600]}`,
                                    outlineOffset: 2,
                                },
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
                            sx={{
                                width: isMobile ? '100%' : 100,
                                ...touchTargetStyles,
                            }}
                            fullWidth={isMobile}
                            size="medium"
                        />
                    </Box>
                )}
            </FormGroup>
        </Box>
    );
};

export default CompetitionFilter;
