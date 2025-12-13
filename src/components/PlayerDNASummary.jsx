import React, { useState, useEffect } from 'react';
import { RefreshCw, Loader2, AlertCircle } from 'lucide-react';
import axios from 'axios';

const PlayerDNASummary = ({ 
  playerName, 
  startDate, 
  endDate, 
  leagues, 
  includeInternational, 
  topTeams, 
  venue 
}) => {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showPatterns, setShowPatterns] = useState(false);

  const fetchSummary = async () => {
    if (!playerName) return;
    
    setLoading(true);
    setError(null);
    
    try {
      // Build query parameters
      const params = new URLSearchParams();
      
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      if (venue) params.append('venue', venue);
      if (includeInternational) params.append('include_international', 'true');
      if (topTeams) params.append('top_teams', topTeams);
      if (showPatterns) params.append('include_patterns', 'true');
      
      // Add leagues
      if (leagues && leagues.length > 0) {
        leagues.forEach(league => params.append('leagues', league));
      }
      
      const response = await axios.get(
        `${process.env.REACT_APP_API_URL}/player-summary/batter/${encodeURIComponent(playerName)}?${params.toString()}`
      );
      
      if (response.data.success) {
        setSummary(response.data);
      } else {
        setError(response.data.error || 'Failed to generate summary');
      }
    } catch (err) {
      console.error('Error fetching summary:', err);
      setError(err.response?.data?.detail || 'Failed to fetch player summary');
    } finally {
      setLoading(false);
    }
  };

  // Fetch on mount and when dependencies change
  useEffect(() => {
    fetchSummary();
  }, [playerName, startDate, endDate, leagues, includeInternational, topTeams, venue]);

  // Parse bullet points from summary text
  const parseSummary = (text) => {
    if (!text) return [];
    
    // Split by newlines and filter out empty lines
    const lines = text.split('\n').filter(line => line.trim());
    
    return lines.map((line, index) => {
      // Extract emoji and text
      const match = line.match(/^([^\s]+)\s+(.+)$/);
      if (match) {
        return {
          emoji: match[1],
          text: match[2]
        };
      }
      return {
        emoji: '•',
        text: line
      };
    });
  };

  if (!playerName) {
    return null;
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xl font-bold text-gray-800">Player DNA</h3>
        <button
          onClick={() => fetchSummary()}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-md transition-colors disabled:opacity-50"
          title="Regenerate summary"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="h-4 w-4" />
          )}
          {loading ? 'Generating...' : 'Refresh'}
        </button>
      </div>

      {loading && !summary && (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
          <span className="ml-3 text-gray-600">Analyzing player patterns...</span>
        </div>
      )}

      {error && (
        <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-md">
          <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-red-800">Error</p>
            <p className="text-sm text-red-700 mt-1">{error}</p>
          </div>
        </div>
      )}

      {summary && summary.success && summary.summary && (
        <div className="space-y-3">
          {parseSummary(summary.summary).map((bullet, index) => (
            <div key={index} className="flex items-start gap-3 p-3 bg-gray-50 rounded-md hover:bg-gray-100 transition-colors">
              <span className="text-2xl flex-shrink-0">{bullet.emoji}</span>
              <p className="text-gray-700 text-sm leading-relaxed pt-1">{bullet.text}</p>
            </div>
          ))}
          
          {summary.cached && (
            <p className="text-xs text-gray-500 italic mt-4">
              Cached result - click refresh to regenerate
            </p>
          )}

          {/* Debug: Show patterns if enabled */}
          {showPatterns && summary.patterns && (
            <details className="mt-4 text-xs">
              <summary className="cursor-pointer text-gray-600 hover:text-gray-800">
                View raw pattern data (debug)
              </summary>
              <pre className="mt-2 p-4 bg-gray-100 rounded overflow-auto max-h-96">
                {JSON.stringify(summary.patterns, null, 2)}
              </pre>
            </details>
          )}
        </div>
      )}
    </div>
  );
};

export default PlayerDNASummary;
