import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
    Box,
    Typography,
    TextField,
    Paper,
    Divider,
    Grid,
    List,
    ListItem,
    ListItemText,
    ListItemIcon,
    Checkbox,
    Button,
    InputAdornment,
    Chip
} from '@mui/material';
import {
    Search as SearchIcon,
    KeyboardArrowRight as KeyboardArrowRightIcon,
    KeyboardArrowLeft as KeyboardArrowLeftIcon,
    Clear as ClearIcon
} from '@mui/icons-material';
import { FixedSizeList } from 'react-window';
import debounce from 'lodash/debounce';
import axios from 'axios';
import config from '../config';

const CustomPlayerSelector = ({ selectedPlayers, onPlayersChange, label = "Custom Players" }) => {
    const [players, setPlayers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [debouncedSearchTerm, setDebouncedSearchTerm] = useState('');
    const [checked, setChecked] = useState([]);

    // Create a debounced search function
    const debouncedSearch = useMemo(
        () =>
            debounce((value) => {
                setDebouncedSearchTerm(value);
            }, 300),
        []
    );

    // Fetch players on component mount
    useEffect(() => {
        const fetchPlayers = async () => {
            try {
                setLoading(true);
                const response = await axios.get(`${config.API_URL}/players/`);
                if (Array.isArray(response.data)) {
                    setPlayers(response.data.sort());
                }
            } catch (error) {
                console.error('Error fetching players:', error);
                setError('Failed to load players');
            } finally {
                setLoading(false);
            }
        };

        fetchPlayers();
    }, []);

    // Memoize filtered players list
    const filteredPlayers = useMemo(() => {
        if (!players.length) return [];
        
        const selectedSet = new Set(selectedPlayers);
        
        return players.filter(player => 
            player.toLowerCase().includes(debouncedSearchTerm.toLowerCase()) &&
            !selectedSet.has(player)
        );
    }, [players, debouncedSearchTerm, selectedPlayers]);

    // Handle search input change
    const handleSearchChange = (event) => {
        setSearchTerm(event.target.value);
        debouncedSearch(event.target.value);
    };

    // Check/uncheck items for transfer
    const handleToggle = useCallback((value) => () => {
        const currentIndex = checked.indexOf(value);
        const newChecked = [...checked];
        
        if (currentIndex === -1) {
            newChecked.push(value);
        } else {
            newChecked.splice(currentIndex, 1);
        }
        
        setChecked(newChecked);
    }, [checked]);

    // Row renderer for virtualized list of available players
    const PlayerRow = useCallback(({ index, style }) => {
        const player = filteredPlayers[index];
        return (
            <ListItem 
                style={style}
                role="listitem"
                button
                onClick={handleToggle(player)}
            >
                <ListItemIcon>
                    <Checkbox
                        checked={checked.indexOf(player) !== -1}
                        tabIndex={-1}
                        disableRipple
                    />
                </ListItemIcon>
                <ListItemText primary={player} />
            </ListItem>
        );
    }, [filteredPlayers, checked, handleToggle]);

    // Row renderer for selected players list
    const SelectedPlayerRow = useCallback(({ index, style }) => {
        const player = selectedPlayers[index];
        return (
            <ListItem
                style={style}
                role="listitem"
                button
                onClick={handleToggle(player)}
            >
                <ListItemIcon>
                    <Checkbox
                        checked={checked.indexOf(player) !== -1}
                        tabIndex={-1}
                        disableRipple
                    />
                </ListItemIcon>
                <ListItemText primary={player} />
            </ListItem>
        );
    }, [selectedPlayers, checked, handleToggle]);

    // Add selected players
    const handleAddPlayers = useCallback(() => {
        const playersToAdd = checked.filter(player => 
            !selectedPlayers.includes(player)
        );
        
        onPlayersChange([...selectedPlayers, ...playersToAdd]);
        setChecked([]);
    }, [checked, selectedPlayers, onPlayersChange]);

    // Remove selected players
    const handleRemovePlayers = useCallback(() => {
        const filteredPlayers = selectedPlayers.filter(player => !checked.includes(player));
        onPlayersChange(filteredPlayers);
        setChecked([]);
    }, [checked, selectedPlayers, onPlayersChange]);

    // Remove individual player
    const handleRemovePlayer = (playerToRemove) => {
        const filteredPlayers = selectedPlayers.filter(player => player !== playerToRemove);
        onPlayersChange(filteredPlayers);
    };

    // Clear all players
    const handleClearAll = () => {
        onPlayersChange([]);
        setChecked([]);
    };

    if (loading) {
        return (
            <Box sx={{ p: 2 }}>
                <Typography>Loading players...</Typography>
            </Box>
        );
    }

    if (error) {
        return (
            <Box sx={{ p: 2 }}>
                <Typography color="error">{error}</Typography>
            </Box>
        );
    }

    return (
        <Box sx={{ mt: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">
                    {label} ({selectedPlayers.length} selected)
                </Typography>
                {selectedPlayers.length > 0 && (
                    <Button
                        variant="outlined"
                        size="small"
                        onClick={handleClearAll}
                        startIcon={<ClearIcon />}
                    >
                        Clear All
                    </Button>
                )}
            </Box>

            {/* Selected Players Display */}
            {selectedPlayers.length > 0 && (
                <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>
                        Selected Players:
                    </Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                        {selectedPlayers.map(player => (
                            <Chip
                                key={player}
                                label={player}
                                onDelete={() => handleRemovePlayer(player)}
                                size="small"
                                variant="outlined"
                            />
                        ))}
                    </Box>
                </Box>
            )}
            
            <Grid container spacing={2}>
                {/* Available Players */}
                <Grid item xs={6}>
                    <Paper sx={{ width: '100%', height: 400, overflow: 'hidden' }}>
                        <Typography variant="subtitle1" sx={{ p: 1 }}>
                            Available Players
                        </Typography>
                        <TextField
                            fullWidth
                            placeholder="Search players..."
                            value={searchTerm}
                            onChange={handleSearchChange}
                            sx={{ p: 1 }}
                            InputProps={{
                                startAdornment: (
                                    <InputAdornment position="start">
                                        <SearchIcon />
                                    </InputAdornment>
                                ),
                            }}
                        />
                        <Divider />
                        {filteredPlayers.length > 0 ? (
                            <FixedSizeList
                                height={300}
                                width="100%"
                                itemSize={46}
                                itemCount={filteredPlayers.length}
                                overscanCount={5}
                            >
                                {PlayerRow}
                            </FixedSizeList>
                        ) : (
                            <Box sx={{ p: 2, textAlign: 'center' }}>
                                <Typography variant="body2" color="textSecondary">
                                    No players found
                                </Typography>
                            </Box>
                        )}
                    </Paper>
                </Grid>
                
                {/* Transfer Controls */}
                <Grid item xs={2} sx={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
                    <Button
                        variant="outlined"
                        size="small"
                        onClick={handleAddPlayers}
                        disabled={checked.length === 0 || !checked.some(item => !selectedPlayers.includes(item))}
                        sx={{ my: 0.5 }}
                    >
                        <KeyboardArrowRightIcon />
                    </Button>
                    <Button
                        variant="outlined"
                        size="small"
                        onClick={handleRemovePlayers}
                        disabled={checked.length === 0 || !checked.some(item => selectedPlayers.includes(item))}
                        sx={{ my: 0.5 }}
                    >
                        <KeyboardArrowLeftIcon />
                    </Button>
                </Grid>
                
                {/* Selected Players */}
                <Grid item xs={4}>
                    <Paper sx={{ width: '100%', height: 400, overflow: 'hidden' }}>
                        <Typography variant="subtitle1" sx={{ p: 1 }}>
                            Selected Players ({selectedPlayers.length})
                        </Typography>
                        <Divider />
                        {selectedPlayers.length === 0 ? (
                            <Box sx={{ p: 2, textAlign: 'center' }}>
                                <Typography variant="body2" color="textSecondary">
                                    No players selected
                                </Typography>
                            </Box>
                        ) : (
                            <FixedSizeList
                                height={300}
                                width="100%"
                                itemSize={46}
                                itemCount={selectedPlayers.length}
                                overscanCount={5}
                            >
                                {SelectedPlayerRow}
                            </FixedSizeList>
                        )}
                        <Divider />
                        <Button
                            variant="outlined"
                            size="small"
                            onClick={handleRemovePlayers}
                            disabled={checked.length === 0 || !checked.some(item => selectedPlayers.includes(item))}
                            sx={{ m: 1 }}
                        >
                            Remove Selected
                        </Button>
                    </Paper>
                </Grid>
            </Grid>
        </Box>
    );
};

export default CustomPlayerSelector;