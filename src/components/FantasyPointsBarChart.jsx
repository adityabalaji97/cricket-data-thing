// FantasyPointsBarChart.jsx component
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const FantasyPointsBarChart = ({ players, title, isMobile }) => {
  // Prepare data for chart
  // Ensure players is an array and has necessary properties
  const validPlayers = Array.isArray(players) ? players.filter(player => 
    player && typeof player === 'object' && player.player_name
  ) : [];
  
  const data = validPlayers.map(player => ({
    name: player.player_name || 'Unknown',
    batting: typeof player.avg_batting_points === 'number' ? player.avg_batting_points : 0,
    bowling: typeof player.avg_bowling_points === 'number' ? player.avg_bowling_points : 0,
    fielding: typeof player.avg_fielding_points === 'number' ? player.avg_fielding_points : 0,
    total: typeof player.avg_fantasy_points === 'number' ? player.avg_fantasy_points : 0
  })).sort((a, b) => b.total - a.total).slice(0, 10); // Top 10 players
  
  return (
    <div className="fantasy-points-chart mb-4">
      {isMobile ? <h5>{title}</h5> : <h4>{title}</h4>}
      <ResponsiveContainer width="100%" height={isMobile ? 300 : 400}>
        <BarChart
          layout="vertical"
          data={data}
          margin={{ top: 20, right: 30, left: isMobile ? 60 : 100, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" label={{ value: 'Fantasy Points', position: 'insideBottom', offset: -5 }} />
          <YAxis type="category" dataKey="name" tick={{ fontSize: isMobile ? 10 : 12 }} width={isMobile ? 60 : 100} />
          <Tooltip formatter={(value) => value.toFixed(1)} />
          <Legend />
          <Bar dataKey="batting" stackId="a" fill="#8884d8" name="Batting" />
          <Bar dataKey="bowling" stackId="a" fill="#82ca9d" name="Bowling" />
          <Bar dataKey="fielding" stackId="a" fill="#ffc658" name="Fielding" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default FantasyPointsBarChart;