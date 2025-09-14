import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  Alert,
  IconButton,
  Tooltip,
  Divider,
  Slider
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import PauseIcon from '@mui/icons-material/Pause';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import DownloadIcon from '@mui/icons-material/Download';
import VideocamIcon from '@mui/icons-material/Videocam';
import config from '../config';

const EloRacerChart = () => {
  const [competitions, setCompetitions] = useState([]);
  const [selectedCompetition, setSelectedCompetition] = useState('international');
  const [startDate, setStartDate] = useState('2023-01-01');
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
  const [eloData, setEloData] = useState({});
  const [chartData, setChartData] = useState([]);
  const [currentData, setCurrentData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isAnimating, setIsAnimating] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [animationSpeed, setAnimationSpeed] = useState(1); // Speed multiplier (0.25x to 2x)
  const [currentDate, setCurrentDate] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const chartRef = useRef(null);

  // Convert speed multiplier to milliseconds (base speed: 400ms)
  const getAnimationDelay = (speedMultiplier) => {
    const baseSpeed = 400; // Base animation speed in ms
    return Math.round(baseSpeed / speedMultiplier);
  };

  // Team-specific colors based on your color scheme
  const getTeamColor = (teamName) => {
    // Handle both full names and abbreviations
    const teamColors = {
      // IPL Teams
      'Chennai Super Kings': '#eff542',
      'CSK': '#eff542',
      'Royal Challengers Bangalore': '#f54242',
      'Royal Challengers Bengaluru': '#f54242',
      'RCB': '#f54242',
      'Mumbai Indians': '#42a7f5',
      'MI': '#42a7f5',
      'Rajasthan Royals': '#FF2AA8',
      'Rising Pune Supergiants': '#FF2AA8',
      'Rising Pune Supergiant': '#FF2AA8',
      'RR': '#FF2AA8',
      'RPSG': '#FF2AA8',
      'Kolkata Knight Riders': '#610048',
      'KKR': '#610048',
      'Kings XI Punjab': '#FF004D',
      'Punjab Kings': '#FF004D',
      'PBKS': '#FF004D',
      'Sunrisers Hyderabad': '#FF7C01',
      'SRH': '#FF7C01',
      'Lucknow Super Giants': '#00BBB3',
      'Pune Warriors': '#00BBB3',
      'LSG': '#00BBB3',
      'Delhi Capitals': '#004BC5',
      'Delhi Daredevils': '#004BC5',
      'DC': '#004BC5',
      'Deccan Chargers': '#04378C',
      'DCh': '#04378C',
      'Gujarat Lions': '#FF5814',
      'GL': '#FF5814',
      'Gujarat Titans': '#01295B',
      'GT': '#01295B',
      'Kochi Tuskers Kerala': '#008080',
      'KTK': '#008080',
      
      // International Teams
      'Australia': '#eff542',
      'AUS': '#eff542',
      'England': '#f54242',
      'ENG': '#f54242',
      'India': '#42a7f5',
      'IND': '#42a7f5',
      'South Africa': '#1cba2e',
      'SA': '#1cba2e',
      'Pakistan': '#02450a',
      'PAK': '#02450a',
      'West Indies': '#450202',
      'WI': '#450202',
      'New Zealand': '#050505',
      'NZ': '#050505',
      'Bangladesh': '#022b07',
      'BAN': '#022b07',
      'Afghanistan': '#058bf2',
      'AFG': '#058bf2',
      'Sri Lanka': '#031459',
      'SL': '#031459',
      'Ireland': '#90EE90',
      'IRE': '#90EE90',
      'Netherlands': '#FF7C01',
      'NED': '#FF7C01',
      'Zimbabwe': '#FF7C01',
      'ZIM': '#FF7C01',
      'Scotland': '#4169E1',
      'SCO': '#4169E1',
      'Nepal': '#DC143C',
      'NEP': '#DC143C',
      'USA': '#B22222',
      'Oman': '#8B0000',
      'OMA': '#8B0000',
      'UAE': '#2F4F4F',
      'Papua New Guinea': '#228B22',
      'PNG': '#228B22',
      'Namibia': '#CD853F',
      'NAM': '#CD853F'
    };
    
    return teamColors[teamName] || '#666666'; // Default color if team not found
  };

  // Fetch available competitions on component mount
  useEffect(() => {
    const fetchCompetitions = async () => {
      try {
        const response = await fetch(`${config.API_URL}/competitions`);
        const data = await response.json();
        setCompetitions(data.leagues || []);
      } catch (error) {
        console.error('Error fetching competitions:', error);
      }
    };
    fetchCompetitions();
  }, []);

  // Fetch ELO history when competition or dates change
  const fetchEloHistory = async () => {
    setLoading(true);
    setError(null);
    
    try {
      let url = `${config.API_URL}/teams/elo-rankings`;
      const params = new URLSearchParams();
      
      // Add date filters
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      
      if (selectedCompetition === 'international') {
        params.append('include_international', 'true');
        params.append('top_teams', '15'); // Top 15 international teams
      } else {
        params.append('league', selectedCompetition);
        params.append('include_international', 'false');
      }
      
      // First get the teams for this competition
      const rankingsResponse = await fetch(`${url}?${params}`);
      if (!rankingsResponse.ok) {
        throw new Error(`HTTP error! status: ${rankingsResponse.status}`);
      }
      
      const rankingsData = await rankingsResponse.json();
      const teams = rankingsData.rankings.map(team => team.team_abbreviation);
      
      if (teams.length === 0) {
        setError('No teams found for the selected competition');
        return;
      }
      
      // Now get ELO history for these teams
      const historyParams = new URLSearchParams();
      teams.forEach(team => {
        historyParams.append('teams', team);
      });
      historyParams.append('start_date', startDate);
      historyParams.append('end_date', endDate);
      
      const historyResponse = await fetch(`${config.API_URL}/teams/elo-history?${historyParams}`);
      if (!historyResponse.ok) {
        throw new Error(`HTTP error! status: ${historyResponse.status}`);
      }
      
      const historyData = await historyResponse.json();
      setEloData(historyData.elo_histories || {});
      
      // Process data for chart
      processChartData(historyData.elo_histories || {});
    } catch (error) {
      console.error('Error fetching ELO history:', error);
      setError('Failed to load ELO history');
    } finally {
      setLoading(false);
    }
  };

  // Process ELO data into chart format
  const processChartData = (histories) => {
    const allDates = new Set();
    
    // Collect all unique dates
    Object.values(histories).forEach(history => {
      history.forEach(point => allDates.add(point.date));
    });
    
    // Sort dates chronologically
    const sortedDates = Array.from(allDates).sort();
    
    // Create chart data points for each date
    const chartPoints = sortedDates.map(date => {
      const teams = [];
      
      Object.keys(histories).forEach(teamName => {
        const teamHistory = histories[teamName];
        // Find the most recent ELO rating for this team up to this date
        const relevantPoints = teamHistory.filter(p => p.date <= date);
        if (relevantPoints.length > 0) {
          const latestPoint = relevantPoints[relevantPoints.length - 1];
          teams.push({
            team: teamName,
            elo: latestPoint.elo,
            result: latestPoint.result
          });
        }
      });
      
      // Sort teams by ELO rating (highest first) and assign positions
      teams.sort((a, b) => b.elo - a.elo);
      teams.forEach((team, index) => {
        team.position = index;
      });
      
      return {
        date,
        teams
      };
    });
    
    setChartData(chartPoints);
    setCurrentIndex(0);
    if (chartPoints.length > 0) {
      setCurrentData(chartPoints[0].teams);
      setCurrentDate(chartPoints[0].date);
    }
  };

  // Animation logic for racer chart
  useEffect(() => {
    let interval;
    if (isAnimating && currentIndex < chartData.length - 1) {
      interval = setInterval(() => {
        setCurrentIndex(prev => {
          const nextIndex = prev + 1;
          if (nextIndex >= chartData.length) {
            setIsAnimating(false);
            return prev;
          }
          
          setCurrentData(chartData[nextIndex].teams);
          setCurrentDate(chartData[nextIndex].date);
          return nextIndex;
        });
      }, getAnimationDelay(animationSpeed)); // Use the converted delay
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isAnimating, currentIndex, chartData.length, animationSpeed]);

  const handleStartAnimation = () => {
    setCurrentIndex(0);
    if (chartData.length > 0) {
      setCurrentData(chartData[0].teams);
      setCurrentDate(chartData[0].date);
    }
    setIsAnimating(true);
  };

  const handlePauseAnimation = () => {
    setIsAnimating(false);
  };

  const handleResetAnimation = () => {
    setIsAnimating(false);
    setCurrentIndex(0);
    if (chartData.length > 0) {
      setCurrentData(chartData[0].teams);
      setCurrentDate(chartData[0].date);
    }
  };

  // Video recording functions
  const generateVideo = async () => {
    if (chartData.length === 0) {
      alert('Please load data first');
      return;
    }
    
    setIsRecording(true);
    
    try {
      // Simple WebM video generation using canvas capture
      const canvas = document.createElement('canvas');
      canvas.width = 1200;
      canvas.height = 800;
      const ctx = canvas.getContext('2d');
      
      // Set up canvas stream
      const stream = canvas.captureStream(30); // 30 FPS
      const recorder = new MediaRecorder(stream, {
        mimeType: 'video/webm;codecs=vp9',
        videoBitsPerSecond: 2500000
      });
      
      const chunks = [];
      
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunks.push(event.data);
        }
      };
      
      recorder.onstop = () => {
        const blob = new Blob(chunks, { type: 'video/webm' });
        downloadBlob(blob, 'webm');
        setIsRecording(false);
      };
      
      // Start recording
      recorder.start();
      
      // Render each frame of the animation
      const frameDuration = getAnimationDelay(animationSpeed);
      
      for (let i = 0; i < chartData.length; i++) {
        // Update chart data
        setCurrentIndex(i);
        setCurrentData(chartData[i].teams);
        setCurrentDate(chartData[i].date);
        
        // Wait for React to render
        await new Promise(resolve => setTimeout(resolve, 50));
        
        // Draw the current chart state to canvas
        await drawChartToCanvas(ctx, chartData[i]);
        
        // Hold this frame for the specified duration
        await new Promise(resolve => setTimeout(resolve, frameDuration));
      }
      
      // Stop recording
      recorder.stop();
      
    } catch (error) {
      console.error('Error generating video:', error);
      alert('Video generation failed. This feature requires a modern browser with MediaRecorder support.');
      setIsRecording(false);
    }
  };
  
  // Draw the chart to canvas
  const drawChartToCanvas = async (ctx, dataPoint) => {
    const { teams, date } = dataPoint;
    
    // Clear canvas
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, 1200, 800);
    
    // Draw title
    ctx.fillStyle = '#000000';
    ctx.font = 'bold 32px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('ELO Rankings Racer Chart', 600, 50);
    
    // Draw date
    ctx.font = '24px Arial';
    ctx.fillStyle = '#1976d2';
    const formattedDate = formatDate(date);
    ctx.fillText(formattedDate, 600, 90);
    
    // Calculate ELO range for bar scaling
    const maxElo = Math.max(...teams.map(team => team.elo), 1000);
    const minElo = Math.min(...teams.map(team => team.elo), 1000);
    const eloRange = maxElo - minElo;
    
    // Draw teams
    const startY = 130;
    const barHeight = 35;
    const rowHeight = 45;
    const maxBarWidth = 600;
    const barStartX = 150;
    
    teams.forEach((team, index) => {
      const y = startY + (index * rowHeight);
      
      // Calculate bar width
      const barWidth = eloRange > 0 ? 
        ((team.elo - minElo) / eloRange) * maxBarWidth * 0.8 + maxBarWidth * 0.15 : 
        maxBarWidth * 0.5;
      
      // Get team color
      const teamColor = getTeamColor(team.team);
      
      // Draw rank
      ctx.fillStyle = team.position < 3 ? '#1976d2' : '#666666';
      ctx.font = 'bold 20px Arial';
      ctx.textAlign = 'center';
      ctx.fillText((team.position + 1).toString(), 40, y + 22);
      
      // Draw team name
      ctx.fillStyle = '#000000';
      ctx.font = '16px Arial';
      ctx.textAlign = 'right';
      ctx.fillText(team.team, barStartX - 10, y + 22);
      
      // Draw bar
      ctx.fillStyle = teamColor;
      ctx.fillRect(barStartX, y, barWidth, barHeight);
      
      // Draw ELO value
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 14px Arial';
      ctx.textAlign = 'right';
      ctx.fillText(team.elo.toString(), barStartX + barWidth - 10, y + 22);
      
      // Draw result indicator if available
      if (team.result) {
        const resultColor = 
          team.result === 'W' ? '#4caf50' : 
          team.result === 'L' ? '#f44336' : '#ff9800';
        
        ctx.fillStyle = resultColor;
        ctx.beginPath();
        ctx.arc(barStartX + barWidth + 25, y + 17, 8, 0, 2 * Math.PI);
        ctx.fill();
        
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 10px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(team.result, barStartX + barWidth + 25, y + 21);
      }
    });
    
    // Draw ELO scale
    ctx.fillStyle = '#666666';
    ctx.font = '12px Arial';
    ctx.textAlign = 'left';
    ctx.fillText(Math.round(minElo).toString(), barStartX, startY + teams.length * rowHeight + 30);
    ctx.textAlign = 'center';
    ctx.fillText('ELO Rating', barStartX + maxBarWidth / 2, startY + teams.length * rowHeight + 30);
    ctx.textAlign = 'right';
    ctx.fillText(Math.round(maxElo).toString(), barStartX + maxBarWidth, startY + teams.length * rowHeight + 30);
  };
  
  // Download helper
  const downloadBlob = (blob, extension) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `elo-racer-${selectedCompetition}-${new Date().toISOString().split('T')[0]}.${extension}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };
  
  const stopRecording = () => {
    // For programmatic generation, we can't really "stop" mid-process
    // This is just for UI consistency
    setIsRecording(false);
  };
  
  // Simplified download function with instructions
  const downloadAsVideo = async () => {
    if (chartData.length === 0) {
      alert('Please load data first');
      return;
    }
    
    const confirmed = window.confirm(
      'Generate video of the ELO racer animation?\n\n' +
      'This will:\n' +
      '• Create a high-quality video file\n' +
      '• Include the full animation sequence\n' +
      '• Take a few moments to process\n' +
      '• Download automatically when complete\n\n' +
      'Continue?'
    );
    
    if (confirmed) {
      await generateVideo();
    }
  };

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  // Get maximum ELO value for scaling
  const maxElo = Math.max(...currentData.map(team => team.elo), 1000);
  const minElo = Math.min(...currentData.map(team => team.elo), 1000);
  const eloRange = maxElo - minElo;

  return (
    <Card sx={{ mt: 4 }}>
      <CardContent>
        <Typography variant="h5" gutterBottom>
          ELO Rankings Racer Chart
        </Typography>
        
        {/* Controls */}
        <Box sx={{ 
          display: 'flex', 
          flexDirection: { xs: 'column', md: 'row' },
          gap: 2, 
          mb: 3,
          alignItems: { xs: 'stretch', md: 'flex-end' }
        }}>
          <FormControl sx={{ minWidth: 200 }}>
            <InputLabel>Competition</InputLabel>
            <Select
              value={selectedCompetition}
              onChange={(e) => setSelectedCompetition(e.target.value)}
              label="Competition"
            >
              <MenuItem value="international">International T20s</MenuItem>
              <Divider />
              {competitions.map((comp) => (
                <MenuItem key={comp.value} value={comp.value}>
                  {comp.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          
          <TextField
            label="Start Date"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            InputLabelProps={{ shrink: true }}
            sx={{ width: { xs: '100%', md: 'auto' } }}
          />
          
          <TextField
            label="End Date"
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            InputLabelProps={{ shrink: true }}
            sx={{ width: { xs: '100%', md: 'auto' } }}
          />
          
          <Button 
            variant="contained" 
            onClick={fetchEloHistory}
            disabled={loading}
            sx={{ height: '56px', width: { xs: '100%', md: 'auto' } }}
          >
            Load Data
          </Button>
        </Box>

        {/* Animation Controls */}
        {chartData.length > 0 && (
          <Box sx={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: 2, 
            mb: 3,
            flexWrap: 'wrap',
            justifyContent: 'space-between'
          }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Tooltip title="Start Animation">
                  <IconButton 
                    onClick={handleStartAnimation}
                    disabled={isAnimating}
                    color="primary"
                    size="large"
                  >
                    <PlayArrowIcon />
                  </IconButton>
                </Tooltip>
                
                <Tooltip title="Pause Animation">
                  <IconButton 
                    onClick={handlePauseAnimation}
                    disabled={!isAnimating}
                    color="primary"
                    size="large"
                  >
                    <PauseIcon />
                  </IconButton>
                </Tooltip>
                
                <Tooltip title="Reset Animation">
                <IconButton 
                onClick={handleResetAnimation}
                color="primary"
                size="large"
                >
                <RestartAltIcon />
                </IconButton>
                </Tooltip>
                </Box>
                
                {/* Video Recording Controls */}
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Tooltip title={isRecording ? "Generating Video..." : "Generate Video"}>
                    <IconButton 
                      onClick={downloadAsVideo}
                      color="error"
                      size="large"
                      disabled={chartData.length === 0 || isRecording}
                      sx={isRecording ? { 
                        animation: 'pulse 1.5s infinite',
                        '@keyframes pulse': {
                          '0%': { opacity: 1 },
                          '50%': { opacity: 0.5 },
                          '100%': { opacity: 1 }
                        }
                      } : {}}
                    >
                      <VideocamIcon />
                    </IconButton>
                  </Tooltip>
                </Box>
              
              <Box sx={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: 1,
                minWidth: 250 // Increased width for better spacing
              }}>
                <Typography variant="body2" sx={{ minWidth: 50 }}>
                  Speed:
                </Typography>
                <Slider
                  value={animationSpeed}
                  onChange={(_, newValue) => setAnimationSpeed(newValue)}
                  min={0.25}
                  max={2}
                  step={0.25}
                  marks={[
                    { value: 0.25, label: '0.25x' },
                    { value: 1, label: '1x' },
                    { value: 2, label: '2x' }
                  ]}
                  valueLabelDisplay="auto"
                  valueLabelFormat={(value) => `${value}x`}
                  sx={{ 
                    flexGrow: 1,
                    '& .MuiSlider-markLabel': {
                      fontSize: '0.75rem',
                      color: 'text.secondary'
                    },
                    '& .MuiSlider-valueLabel': {
                      fontSize: '0.75rem'
                    }
                  }}
                />
              </Box>
            </Box>
            
            <Box sx={{ textAlign: 'right' }}>
              <Typography variant="h6" color="primary">
                {formatDate(currentDate)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {currentIndex + 1} / {chartData.length} data points
              </Typography>
            </Box>
          </Box>
        )}

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        ) : currentData.length > 0 ? (
          <Box 
            ref={chartRef}
            sx={{ 
              height: Math.max(400, currentData.length * 50), 
              width: '100%',
              position: 'relative',
              overflow: 'hidden'
            }}>
            {/* Chart Container */}
            <Box sx={{ 
              position: 'relative',
              height: '100%',
              py: 2
            }}>
              {currentData.map((team) => {
                const barWidth = eloRange > 0 ? ((team.elo - minElo) / eloRange) * 80 + 15 : 50;
                const color = getTeamColor(team.team); // Use team-specific color
                const topPosition = team.position * 50 + 16; // 50px per row + padding
                
                return (
                  <Box 
                    key={team.team}
                    sx={{
                      position: 'absolute',
                      top: `${topPosition}px`,
                      left: 0,
                      right: 0,
                      display: 'flex',
                      alignItems: 'center',
                      height: 40,
                      transition: 'top 0.5s cubic-bezier(0.4, 0, 0.2, 1)', // Smooth position transition
                      zIndex: currentData.length - team.position // Higher rank = higher z-index
                    }}
                  >
                    {/* Rank */}
                    <Box sx={{
                      width: 40,
                      textAlign: 'center',
                      fontWeight: 'bold',
                      fontSize: '1.1rem',
                      color: team.position < 3 ? 'primary.main' : 'text.secondary',
                      transition: 'color 0.3s ease'
                    }}>
                      {team.position + 1}
                    </Box>
                    
                    {/* Team Name */}
                    <Box sx={{
                      width: 60,
                      textAlign: 'right',
                      pr: 2,
                      fontWeight: 'medium',
                      fontSize: '0.9rem'
                    }}>
                      {team.team}
                    </Box>
                    
                    {/* Bar */}
                    <Box sx={{
                      flexGrow: 1,
                      position: 'relative',
                      height: 32,
                      display: 'flex',
                      alignItems: 'center'
                    }}>
                      <Box
                        sx={{
                          width: `${barWidth}%`,
                          height: '100%',
                          backgroundColor: color,
                          borderRadius: 1,
                          position: 'relative',
                          transition: 'width 0.5s ease-out', // Smooth bar width transition
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'flex-end',
                          pr: 1,
                          minWidth: 60,
                          boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                        }}
                      >
                        <Typography 
                          variant="body2" 
                          sx={{ 
                            color: 'white', 
                            fontWeight: 'bold',
                            textShadow: '1px 1px 2px rgba(0,0,0,0.5)',
                            transition: 'all 0.3s ease'
                          }}
                        >
                          {team.elo}
                        </Typography>
                      </Box>
                    </Box>
                    
                    {/* Recent Result */}
                    {team.result && (
                      <Box sx={{
                        width: 30,
                        textAlign: 'center',
                        ml: 1
                      }}>
                        <Box sx={{
                          width: 20,
                          height: 20,
                          borderRadius: '50%',
                          backgroundColor: 
                            team.result === 'W' ? 'success.main' : 
                            team.result === 'L' ? 'error.main' : 'warning.main',
                          color: 'white',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: '0.75rem',
                          fontWeight: 'bold',
                          transition: 'all 0.3s ease'
                        }}>
                          {team.result}
                        </Box>
                      </Box>
                    )}
                  </Box>
                );
              })}
            </Box>
            
            {/* ELO Scale */}
            <Box sx={{
              display: 'flex',
              justifyContent: 'space-between',
              mt: 2,
              px: 13,
              borderTop: 1,
              borderColor: 'divider',
              pt: 1
            }}>
              <Typography variant="caption" color="text.secondary">
                {Math.round(minElo)}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                ELO Rating
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {Math.round(maxElo)}
              </Typography>
            </Box>
          </Box>
        ) : (
          !loading && (
            <Typography 
              variant="body1" 
              color="text.secondary" 
              align="center" 
              sx={{ py: 4 }}
            >
              Select a competition and click "Load Data" to view ELO rankings race
            </Typography>
          )
        )}
      </CardContent>
    </Card>
  );
};

export default EloRacerChart;