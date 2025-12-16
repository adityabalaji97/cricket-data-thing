import React from 'react';
import { Box, Typography } from '@mui/material';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import { useNavigate } from 'react-router-dom';

const EloMoversCard = ({ data }) => {
  const navigate = useNavigate();

  if (data.error) {
    return <Typography>{data.error}</Typography>;
  }

  const handleTeamClick = (teamName) => {
    navigate(`/team?team=${encodeURIComponent(teamName)}&start_date=2025-01-01&end_date=2025-12-31&autoload=true`);
  };

  return (
    <Box className="elo-movers-content">
      {/* Risers Section */}
      <Box className="movers-section risers">
        <Typography variant="h6" className="section-title" sx={{ color: '#4CAF50' }}>
          <TrendingUpIcon /> Biggest Risers
        </Typography>
        {data.risers?.length > 0 ? (
          data.risers.map((team) => (
            <Box 
              key={team.team} 
              className="mover-item"
              onClick={(e) => {
                e.stopPropagation();
                handleTeamClick(team.team);
              }}
            >
              <Typography variant="body1" className="team-name">{team.team}</Typography>
              <Box className="elo-change positive">
                <Typography variant="h6">+{Math.round(team.elo_change)}</Typography>
                <Typography variant="caption">
                  {Math.round(team.start_elo)} → {Math.round(team.end_elo)}
                </Typography>
              </Box>
            </Box>
          ))
        ) : (
          <Typography variant="body2" sx={{ color: '#666' }}>No data available</Typography>
        )}
      </Box>

      {/* Fallers Section */}
      <Box className="movers-section fallers">
        <Typography variant="h6" className="section-title" sx={{ color: '#f44336' }}>
          <TrendingDownIcon /> Biggest Fallers
        </Typography>
        {data.fallers?.length > 0 ? (
          data.fallers.map((team) => (
            <Box 
              key={team.team} 
              className="mover-item"
              onClick={(e) => {
                e.stopPropagation();
                handleTeamClick(team.team);
              }}
            >
              <Typography variant="body1" className="team-name">{team.team}</Typography>
              <Box className="elo-change negative">
                <Typography variant="h6">{Math.round(team.elo_change)}</Typography>
                <Typography variant="caption">
                  {Math.round(team.start_elo)} → {Math.round(team.end_elo)}
                </Typography>
              </Box>
            </Box>
          ))
        ) : (
          <Typography variant="body2" sx={{ color: '#666' }}>No data available</Typography>
        )}
      </Box>
    </Box>
  );
};

export default EloMoversCard;
