import React, { useMemo } from 'react';
import { getBatterColor, getWeekStart } from './contributionGraphUtils';

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

const ContributionGraph = ({ innings, playerName }) => {
  const { weeks, monthLabels, stats, totalYears } = useMemo(() => {
    if (!innings || innings.length === 0) {
      return { weeks: [], monthLabels: [], stats: { total: 0, avgFantasy: 0, ducks: 0 }, totalYears: 0 };
    }

    // Sort innings by date
    const sorted = [...innings].sort((a, b) => new Date(a.date) - new Date(b.date));
    
    // Get date range
    const startDate = new Date(sorted[0].date);
    const endDate = new Date(sorted[sorted.length - 1].date);
    
    // Calculate total years spanned
    const msPerYear = 365.25 * 24 * 60 * 60 * 1000;
    const yearsSpanned = (endDate - startDate) / msPerYear;
    
    // Create a map for quick lookup
    const inningsMap = new Map();
    sorted.forEach(inn => {
      const key = inn.date;
      if (!inningsMap.has(key)) {
        inningsMap.set(key, []);
      }
      inningsMap.get(key).push(inn);
    });

    // Generate weeks from start to end
    const weeksData = [];
    const labels = [];
    let currentDate = getWeekStart(startDate);
    let lastMonthYear = '';
    let weekIndex = 0;

    while (currentDate <= endDate) {
      const week = [];
      const weekStart = new Date(currentDate);
      
      for (let d = 0; d < 7; d++) {
        const day = new Date(currentDate);
        day.setDate(day.getDate() + d);
        
        const dateStr = day.toISOString().split('T')[0];
        const dayInnings = inningsMap.get(dateStr) || [];
        
        week.push({
          date: dateStr,
          dayOfWeek: day.getDay(),
          innings: dayInnings,
          isInRange: day >= startDate && day <= endDate
        });
      }
      
      weeksData.push(week);
      
      // Track month changes for labels - use month+year to avoid duplicate detection
      const month = weekStart.getMonth();
      const year = weekStart.getFullYear();
      const monthYear = `${year}-${month}`;
      if (monthYear !== lastMonthYear) {
        labels.push({ weekIndex, month, year });
        lastMonthYear = monthYear;
      }
      
      currentDate.setDate(currentDate.getDate() + 7);
      weekIndex++;
    }

    // Calculate stats
    const total = innings.length;
    const fantasyPoints = innings.map(i => i.fantasy_points || 0);
    const avgFantasy = fantasyPoints.length > 0 
      ? fantasyPoints.reduce((a, b) => a + b, 0) / fantasyPoints.length 
      : 0;
    const ducks = innings.filter(i => i.runs === 0 && i.balls_faced > 0).length;

    return { 
      weeks: weeksData, 
      monthLabels: labels, 
      stats: { total, avgFantasy, ducks },
      totalYears: yearsSpanned
    };
  }, [innings]);

  if (!innings || innings.length === 0) {
    return null;
  }

  // Determine label format based on time span
  const useSingleLetter = totalYears > 3;
  const labelSkip = totalYears > 5 ? 3 : totalYears > 3 ? 2 : 1;

  const CELL_SIZE = 10;
  const CELL_GAP = 2;
  const WEEK_WIDTH = CELL_SIZE + CELL_GAP;
  const LEFT_PADDING = 28;
  const TOP_PADDING = 16;

  const svgWidth = LEFT_PADDING + (weeks.length * WEEK_WIDTH) + 10;
  const svgHeight = TOP_PADDING + (7 * WEEK_WIDTH) + 10;

  return (
    <div style={{ 
      background: '#fff', 
      borderRadius: '8px', 
      padding: '16px',
      border: '1px solid #e1e4e8',
      marginBottom: '20px'
    }}>
      <div style={{ marginBottom: '8px' }}>
        <div style={{ fontWeight: 600, fontSize: '14px', marginBottom: '4px' }}>Performance Graph</div>
        <div style={{ color: '#666', fontSize: '12px' }}>
          <span>{stats.total} innings</span>
          <span style={{ marginLeft: '12px' }}>
            Avg Fantasy: {stats.avgFantasy.toFixed(1)} pts
          </span>
          <span style={{ marginLeft: '12px' }}>
            🦆 {stats.ducks} ducks
          </span>
        </div>
      </div>
      
      <div style={{ overflowX: 'auto' }}>
        <svg width={svgWidth} height={svgHeight} style={{ display: 'block' }}>
          {/* Month labels */}
          {monthLabels.map((label, idx) => {
            // Skip labels based on time span
            if (idx % labelSkip !== 0) return null;
            
            const monthNames = useSingleLetter 
              ? ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D']
              : ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            
            // Show year on January or first label
            const showYear = label.month === 0 || idx === 0;
            const labelText = useSingleLetter 
              ? (showYear ? `${monthNames[label.month]}'${String(label.year).slice(2)}` : monthNames[label.month])
              : monthNames[label.month];
            
            return (
              <text
                key={`${label.weekIndex}-${label.month}-${label.year}`}
                x={LEFT_PADDING + (label.weekIndex * WEEK_WIDTH)}
                y={10}
                fontSize="9"
                fill="#666"
              >
                {labelText}
              </text>
            );
          })}
          
          {/* Day labels */}
          {DAYS.map((day, idx) => (
            idx % 2 === 1 && (
              <text
                key={day}
                x={2}
                y={TOP_PADDING + (idx * WEEK_WIDTH) + 8}
                fontSize="9"
                fill="#666"
              >
                {day}
              </text>
            )
          ))}
          
          {/* Grid cells */}
          {weeks.map((week, weekIdx) => (
            <g key={weekIdx}>
              {week.map((day, dayIdx) => {
                if (!day.isInRange) return null;
                
                const hasInnings = day.innings.length > 0;
                const totalFantasy = day.innings.reduce((sum, inn) => sum + (inn.fantasy_points || 0), 0);
                const isDuck = day.innings.some(inn => inn.runs === 0 && inn.balls_faced > 0);
                const color = getBatterColor(totalFantasy, isDuck);
                
                // Create tooltip text
                const tooltipText = hasInnings 
                  ? `${day.date}: ${day.innings.map(inn => 
                      `${inn.runs}(${inn.balls_faced}) vs ${inn.bowling_team} - ${inn.fantasy_points?.toFixed(1) || 0} pts`
                    ).join(', ')}`
                  : '';
                
                const cellX = LEFT_PADDING + (weekIdx * WEEK_WIDTH);
                const cellY = TOP_PADDING + (dayIdx * WEEK_WIDTH);
                
                return (
                  <g key={`${weekIdx}-${dayIdx}`}>
                    <rect
                      x={cellX}
                      y={cellY}
                      width={CELL_SIZE}
                      height={CELL_SIZE}
                      rx={2}
                      fill={color}
                      style={{ cursor: hasInnings ? 'pointer' : 'default' }}
                    >
                      {hasInnings && (
                        <title>{tooltipText}</title>
                      )}
                    </rect>
                    {isDuck && (
                      <text
                        x={cellX + CELL_SIZE / 2}
                        y={cellY + CELL_SIZE / 2 + 1}
                        fontSize="7"
                        textAnchor="middle"
                        dominantBaseline="middle"
                        style={{ pointerEvents: 'none', userSelect: 'none' }}
                      >
                        🦆
                      </text>
                    )}
                  </g>
                );
              })}
            </g>
          ))}
        </svg>
      </div>
      
      {/* Legend */}
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        gap: '4px', 
        marginTop: '8px',
        fontSize: '11px',
        color: '#666'
      }}>
        <span>Less</span>
        {['#ebedf0', '#9be9a8', '#40c463', '#30a14e', '#216e39'].map((color, i) => (
          <div
            key={i}
            style={{
              width: '10px',
              height: '10px',
              backgroundColor: color,
              borderRadius: '2px'
            }}
          />
        ))}
        <span>More</span>
        <span style={{ marginLeft: '12px' }}>🦆 Duck</span>
      </div>
    </div>
  );
};

export default ContributionGraph;
