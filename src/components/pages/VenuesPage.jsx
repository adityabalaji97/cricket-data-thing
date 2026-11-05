import React, { useEffect, useState } from 'react';
import { Autocomplete, Box, TextField } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import config from '../../config';
import { colors, fonts } from '../../theme/hindsightDark';

// Venues (the menu overhaul, 5 Nov 2026): pick a ground for its page (/venue?venue=…, the match preview with no teams).
const VenuesPage = () => {
  const navigate = useNavigate();
  const [venues, setVenues] = useState([]);
  useEffect(() => {
    document.title = 'Venues · Hindsight';
    fetch(`${config.API_URL}/venues/`).then((r) => r.json())
      .then((d) => setVenues((Array.isArray(d) ? d : []).filter(Boolean).sort()))
      .catch(() => setVenues([]));
  }, []);
  return (
    <Box sx={{ px: 2, pt: 3, display: 'flex', flexDirection: 'column', gap: 1.5, maxWidth: 520, mx: 'auto', color: colors.textHi }}>
      <Box component="h1" sx={{ m: 0, fontFamily: fonts.display, fontWeight: 700, fontSize: 28 }}>Venues</Box>
      <Box sx={{ color: colors.textLo, fontSize: 14 }}>How does a ground play? Pick one.</Box>
      <Autocomplete options={venues} onChange={(_, v) => v && navigate(`/venue?venue=${encodeURIComponent(v)}`)}
        renderInput={(params) => <TextField {...params} label="Ground" autoFocus />} />
    </Box>
  );
};

export default VenuesPage;
