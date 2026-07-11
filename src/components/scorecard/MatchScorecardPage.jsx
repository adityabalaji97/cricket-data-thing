import React, { useEffect, useRef, useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import config from '../../config';
import './matchScorecard.css';

const SCREEN_OPTIONS = [
  { key: 'summary', label: 'Summary' },
  { key: 'batting', label: 'Batting' },
  { key: 'bowling', label: 'Bowling' },
];

const BAT_LENSES = [
  { key: 'bowler', label: 'vs Bowler' },
  { key: 'phase', label: 'Phase' },
  { key: 'pace', label: 'Pace / Spin' },
  { key: 'zones', label: 'Zones' },
  { key: 'grid', label: 'Line.Len' },
];

const BOWL_LENSES = [
  { key: 'batter', label: 'vs Batter' },
  { key: 'phase', label: 'Phase' },
  { key: 'hand', label: 'RH / LH' },
  { key: 'zones', label: 'Zones' },
  { key: 'grid', label: 'Line.Len' },
];

const getAccent = (data, team, fallback = '#f0b429') => (
  data?.match?.teams?.find((item) => item.name === team)?.accent || fallback
);

const getScreen = (params) => {
  const value = params.get('screen');
  return ['summary', 'batting', 'bowling'].includes(value) ? value : 'summary';
};

const getNumber = (value, fallback) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

const setParam = (searchParams, setSearchParams, updates) => {
  const next = new URLSearchParams(searchParams);
  Object.entries(updates).forEach(([key, value]) => {
    if (value === null || value === undefined || value === '') {
      next.delete(key);
    } else {
      next.set(key, String(value));
    }
  });
  setSearchParams(next);
};

const scrollToTarget = (id) => {
  if (!id) return;
  requestAnimationFrame(() => {
    setTimeout(() => {
      const el = document.getElementById(id);
      if (!el) return;
      window.scrollTo({
        top: el.getBoundingClientRect().top + window.scrollY - 40,
        behavior: 'smooth',
      });
    }, 80);
  });
};

const MatchScorecardPage = () => {
  const { matchId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const targetHandledRef = useRef('');
  const minBalls = searchParams.get('min_balls') || 6;

  useEffect(() => {
    let cancelled = false;
    const fetchScorecard = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await axios.get(`${config.API_URL}/matches/${matchId}/scorecard`, {
          params: { min_balls: minBalls },
        });
        if (!cancelled) setData(response.data);
      } catch (err) {
        if (!cancelled) {
          setError(err.response?.data?.detail || err.message || 'Failed to load scorecard');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetchScorecard();
    return () => {
      cancelled = true;
    };
  }, [matchId, minBalls]);

  const screen = getScreen(searchParams);
  const inningsNumber = getNumber(searchParams.get('innings'), data?.innings?.[0]?.innings || 1);
  const innings = data?.innings?.find((item) => item.innings === inningsNumber) || data?.innings?.[0];
  const target = searchParams.get('target');

  useEffect(() => {
    if (!data || !target || targetHandledRef.current === target) return;
    targetHandledRef.current = target;
    scrollToTarget(target);
  }, [data, target, screen, inningsNumber]);

  if (loading) {
    return <div className="scorecard-page"><div className="scorecard-shell"><div className="scorecard-loading">Loading scorecard...</div></div></div>;
  }

  if (error || !data) {
    return <div className="scorecard-page"><div className="scorecard-shell"><div className="scorecard-error">{error || 'Scorecard unavailable'}</div></div></div>;
  }

  return (
    <div className="scorecard-page">
      <div className="scorecard-shell">
        <ScorecardTopNav
          data={data}
          screen={screen}
          setScreen={(nextScreen) => setParam(searchParams, setSearchParams, { screen: nextScreen, target: null })}
        />

        {screen !== 'summary' && (
          <InningsPicker
            innings={data.innings}
            active={innings?.innings}
            onChange={(nextInnings) => setParam(searchParams, setSearchParams, {
              innings: nextInnings,
              openBatter: null,
              openBowler: null,
              target: null,
            })}
          />
        )}

        {screen === 'summary' && <ScorecardSummaryScreen data={data} />}
        {screen === 'batting' && innings && (
          <BattingBreakdownScreen
            data={data}
            innings={innings}
            searchParams={searchParams}
            setSearchParams={setSearchParams}
          />
        )}
        {screen === 'bowling' && innings && (
          <BowlingBreakdownScreen
            data={data}
            innings={innings}
            searchParams={searchParams}
            setSearchParams={setSearchParams}
          />
        )}
      </div>
    </div>
  );
};

const ScorecardTopNav = ({ data, screen, setScreen }) => (
  <header className="scorecard-top">
    <div>
      <div className="scorecard-kicker">{data.match.competition || data.match.event_name || 'Match Scorecard'}</div>
      <h1>{data.match.team1} vs {data.match.team2}</h1>
      <p>{data.match.venue}{data.match.city ? `, ${data.match.city}` : ''}</p>
    </div>
    <div className="scorecard-screen-tabs" role="tablist">
      {SCREEN_OPTIONS.map((option) => (
        <button
          key={option.key}
          className={screen === option.key ? 'active' : ''}
          onClick={() => setScreen(option.key)}
          type="button"
        >
          {option.label}
        </button>
      ))}
    </div>
  </header>
);

const InningsPicker = ({ innings, active, onChange }) => (
  <div className="innings-picker">
    {innings.map((item) => (
      <button
        key={item.innings}
        type="button"
        className={active === item.innings ? 'active' : ''}
        onClick={() => onChange(item.innings)}
      >
        <span>{item.batting_team}</span>
        <b>{item.score.runs}/{item.score.wickets}</b>
      </button>
    ))}
  </div>
);

const ScorecardSummaryScreen = ({ data }) => {
  const [fullOpen, setFullOpen] = useState(false);
  const winnerAccent = getAccent(data, data.match.winner);
  const winnerPrefix = data.match.winner ? `${data.match.winner} won by ` : '';
  const hasWinnerMargin = winnerPrefix && data.match.result_text?.startsWith(winnerPrefix);

  return (
    <main>
      <section className="result-card">
        <div className="scorecard-kicker">Result {data.match.venue ? `- ${data.match.venue}` : ''}</div>
        <h2>{hasWinnerMargin ? (
          <>
            {data.match.winner} won by <span style={{ color: winnerAccent }}>{data.match.result_text.replace(winnerPrefix, '')}</span>
          </>
        ) : data.match.result_text}</h2>
        {data.match.chase_note && <p>{data.match.chase_note}</p>}
        <div className="score-lines">
          {data.summary.innings_scores.map((score) => (
            <div className="score-line" key={score.innings} style={{ '--team-accent': getAccent(data, score.team) }}>
              <span className="team-dot" />
              <span>{score.team}</span>
              <b>{score.runs}<small>/{score.wickets}</small></b>
              <em>{score.overs}</em>
            </div>
          ))}
        </div>
      </section>

      <MomentCard moment={data.summary.moment} playerOfMatch={data.match.player_of_match} />
      <MomentumWorm data={data} />
      <PlayerOfMatchCard player={data.match.player_of_match} />
      <TopPerformers data={data} />

      <section className="scorecard-collapse">
        <button type="button" onClick={() => setFullOpen((value) => !value)}>
          <span>{fullOpen ? 'Hide full scorecard' : 'View full scorecard'}</span>
          <b>tap</b>
        </button>
        <div className={`full-scorecard ${fullOpen ? 'open' : ''}`}>
          {data.innings.map((item) => (
            <FullInnings key={item.innings} data={data} innings={item} />
          ))}
        </div>
      </section>
    </main>
  );
};

const MomentCard = ({ moment, playerOfMatch }) => (
  <section className="moment-card">
    <div className="scorecard-kicker">The moment</div>
    <h2>{moment?.title || 'Decisive passage'}</h2>
    <p>{moment?.subtitle || `${playerOfMatch || 'The player of the match'} shaped the result.`}</p>
    {moment?.chips?.length > 0 && (
      <div className="moment-chips">
        {moment.chips.map((chip, index) => <span key={`${chip}-${index}`}>{chip}</span>)}
      </div>
    )}
  </section>
);

const MomentumWorm = ({ data }) => (
  <section className="worm-card">
    <div className="card-heading-row">
      <span>Momentum</span>
      <div>
        {data.summary.worm.map((line) => (
          <em key={line.innings} style={{ color: getAccent(data, line.team) }}>{line.team}</em>
        ))}
      </div>
    </div>
    <svg viewBox="0 0 100 60" preserveAspectRatio="none" width="100%" height="168">
      <line x1="0" y1="4" x2="100" y2="4" />
      <line x1="0" y1="32" x2="100" y2="32" />
      <line x1="0" y1="60" x2="100" y2="60" className="base" />
      {data.summary.worm.map((line) => (
        <polyline
          key={line.innings}
          points={line.points}
          fill="none"
          stroke={getAccent(data, line.team)}
          strokeWidth="2.5"
          strokeLinejoin="round"
          strokeLinecap="round"
          vectorEffect="non-scaling-stroke"
        />
      ))}
    </svg>
    <div className="worm-axis"><span>Ov 5</span><span>10</span><span>15</span><span>20</span></div>
  </section>
);

const PlayerOfMatchCard = ({ player }) => (
  <section className="pom-card">
    <div className="photo-block">PHOTO</div>
    <div>
      <div className="scorecard-kicker gold">Player of the match</div>
      <h2>{player || 'Unavailable'}</h2>
      <p>Official match award</p>
    </div>
  </section>
);

const TopPerformers = ({ data }) => (
  <section className="top-performers">
    <div className="section-label">Top performers</div>
    <div className="performer-grid">
      {data.summary.top_performers.map((item, index) => (
        <div className="performer-card" key={`${item.kind}-${item.team}-${item.player}`} style={{ '--team-accent': getAccent(data, item.team, index % 2 ? '#5b8def' : '#f0b429') }}>
          <span>{item.kind === 'top_bat' ? 'TOP BAT' : 'TOP WKT'} - {item.team}</span>
          <b>{item.player}</b>
          <strong>{item.label}</strong>
        </div>
      ))}
    </div>
  </section>
);

const FullInnings = ({ data, innings }) => (
  <section className="full-innings">
    <div className="full-innings-title">
      <b>{innings.batting_team} <span style={{ color: getAccent(data, innings.batting_team) }}>{innings.score.runs}/{innings.score.wickets}</span></b>
      <span>RR {innings.score.run_rate}</span>
    </div>
    <div className="mini-table header"><span>BATTER</span><span>R</span><span>B</span><span>4s</span><span>6s</span></div>
    {innings.batting.map((row) => (
      <div className="mini-table" key={row.id}>
        <span><b>{row.name}</b><small>{row.dismissal}</small></span>
        <span>{row.runs}</span><span>{row.balls}</span><span>{row.fours}</span><span>{row.sixes}</span>
      </div>
    ))}
    <div className="section-label">{innings.bowling_team} bowling</div>
    {innings.bowling.map((row) => (
      <div className="bowling-mini-row" key={row.id}>
        <span>{row.name}</span><em>{row.figures}</em><b>{row.wickets}</b>
      </div>
    ))}
  </section>
);

const BattingBreakdownScreen = ({ data, innings, searchParams, setSearchParams }) => {
  const lens = searchParams.get('batLens') || 'bowler';
  const openId = searchParams.get('openBatter') || innings.batting[0]?.id;

  return (
    <main>
      <ScreenHeader
        kicker={`${innings.batting_team} innings - Scorecard`}
        title={<>{innings.batting_team} <span style={{ color: getAccent(data, innings.batting_team) }}>{innings.score.runs}/{innings.score.wickets}</span></>}
        subtitle="Tap a batter for their ball-by-ball breakdown"
      />
      <div className="scorecard-row-header batting"><span>BATTER</span><span>R</span><span>B</span><span>SR</span></div>
      <div className="accordion-list">
        {innings.batting.map((player) => (
          <BatterAccordionRow
            key={player.id}
            data={data}
            innings={innings}
            player={player}
            open={openId === player.id}
            lens={lens}
            onToggle={() => setParam(searchParams, setSearchParams, { openBatter: openId === player.id ? null : player.id, target: null })}
            onLens={(nextLens) => setParam(searchParams, setSearchParams, { batLens: nextLens })}
            onCrossLink={(bowlerId) => setParam(searchParams, setSearchParams, {
              screen: 'bowling',
              innings: innings.innings,
              openBowler: bowlerId,
              bowlLens: 'batter',
              target: `bowler-${innings.innings}-${bowlerId}`,
            })}
          />
        ))}
      </div>
    </main>
  );
};

const BowlingBreakdownScreen = ({ data, innings, searchParams, setSearchParams }) => {
  const lens = searchParams.get('bowlLens') || 'batter';
  const openId = searchParams.get('openBowler') || innings.bowling[0]?.id;

  return (
    <main>
      <ScreenHeader
        kicker={`${innings.bowling_team} bowling`}
        title={<>{innings.bowling_team} <span style={{ color: getAccent(data, innings.bowling_team) }}>bowling</span></>}
        subtitle="Tap a bowler for their ball-by-ball breakdown"
      />
      <div className="scorecard-row-header bowling"><span>BOWLER</span><span>O</span><span>R</span><span>W</span></div>
      <div className="accordion-list">
        {innings.bowling.map((player) => (
          <BowlerAccordionRow
            key={player.id}
            data={data}
            innings={innings}
            player={player}
            open={openId === player.id}
            lens={lens}
            onToggle={() => setParam(searchParams, setSearchParams, { openBowler: openId === player.id ? null : player.id, target: null })}
            onLens={(nextLens) => setParam(searchParams, setSearchParams, { bowlLens: nextLens })}
            onCrossLink={(batterId) => setParam(searchParams, setSearchParams, {
              screen: 'batting',
              innings: innings.innings,
              openBatter: batterId,
              batLens: 'bowler',
              target: `batter-${innings.innings}-${batterId}`,
            })}
          />
        ))}
      </div>
    </main>
  );
};

const ScreenHeader = ({ kicker, title, subtitle }) => (
  <section className="screen-header">
    <div className="scorecard-kicker">{kicker}</div>
    <h2>{title}</h2>
    <p>{subtitle}</p>
  </section>
);

const BatterAccordionRow = ({ data, innings, player, open, lens, onToggle, onLens, onCrossLink }) => (
  <article id={`batter-${innings.innings}-${player.id}`} className="scorecard-accordion-row">
    <button type="button" className="accordion-trigger batting" onClick={onToggle}>
      <span className="player-name">{player.name}<small>{player.dismissal}</small></span>
      <b>{player.runs}</b><em>{player.balls}</em><strong>{player.strike_rate}</strong>
    </button>
    {open && (
      <div className="accordion-panel">
        <SegmentedControl options={BAT_LENSES} value={lens} onChange={onLens} />
        {lens === 'bowler' && <BatVsBowler player={player} innings={innings} onCrossLink={onCrossLink} />}
        {lens === 'phase' && <PhaseCards rows={player.breakdowns.phase} batting />}
        {lens === 'pace' && <SplitCards rows={player.breakdowns.pace_spin} batting />}
        {lens === 'zones' && <WagonSpokes rows={player.breakdowns.zones} color={getAccent(data, innings.batting_team)} />}
        {lens === 'grid' && <LineLengthHeatmap rows={player.breakdowns.line_length} batting />}
      </div>
    )}
  </article>
);

const BowlerAccordionRow = ({ data, innings, player, open, lens, onToggle, onLens, onCrossLink }) => (
  <article id={`bowler-${innings.innings}-${player.id}`} className="scorecard-accordion-row">
    <button type="button" className="accordion-trigger bowling" onClick={onToggle}>
      <span className="player-name">{player.name}<small>{player.style || 'Bowler'}</small></span>
      <b>{player.overs}</b><em>{player.runs}</em><strong>{player.wickets}</strong>
    </button>
    {open && (
      <div className="accordion-panel">
        <SegmentedControl options={BOWL_LENSES} value={lens} onChange={onLens} />
        {lens === 'batter' && <BowlVsBatter player={player} innings={innings} onCrossLink={onCrossLink} />}
        {lens === 'phase' && <PhaseCards rows={player.breakdowns.phase} />}
        {lens === 'hand' && <HandCards rows={player.breakdowns.hand} />}
        {lens === 'zones' && <WagonSpokes rows={player.breakdowns.zones} color="#e5484d" bowling />}
        {lens === 'grid' && <LineLengthHeatmap rows={player.breakdowns.line_length} />}
      </div>
    )}
  </article>
);

const SegmentedControl = ({ options, value, onChange }) => (
  <div className="scorecard-segmented">
    {options.map((option) => (
      <button key={option.key} type="button" className={value === option.key ? 'active' : ''} onClick={() => onChange(option.key)}>
        {option.label}
      </button>
    ))}
  </div>
);

const BatVsBowler = ({ player, innings, onCrossLink }) => (
  <div>
    <div className="panel-title">{player.name} vs each bowler</div>
    {player.breakdowns.vs_bowler.rows.map((row) => {
      const linkable = innings.bowling.some((item) => item.id === row.id);
      return (
        <div className="matchup-bar-row" key={row.id} onClick={() => linkable && onCrossLink(row.id)} role={linkable ? 'button' : undefined}>
          <div className="bar-row-top">
            <span>{row.name}{linkable && <button type="button" className="cross-link"> &gt; BOWLING</button>}</span>
            <b>{row.runs} <small>({row.balls})</small></b>
          </div>
          <MetricBar pct={row.bar_pct} color="linear-gradient(90deg,#f0b429,#f7d774)" />
          <div className="metric-trail"><strong>SR {row.sr}</strong><span>{row.fours}x4</span><span>{row.sixes}x6</span><span>{row.dots} dots</span></div>
        </div>
      );
    })}
  </div>
);

const BowlVsBatter = ({ player, innings, onCrossLink }) => (
  <div>
    <div className="panel-title">{player.name} vs each batter</div>
    {player.breakdowns.vs_batter.rows.map((row) => {
      const linkable = innings.batting.some((item) => item.id === row.id);
      return (
        <div className="matchup-bar-row" key={row.id} onClick={() => linkable && onCrossLink(row.id)} role={linkable ? 'button' : undefined}>
          <div className="bar-row-top">
            <span>{row.name}{linkable && <button type="button" className="cross-link gold-link"> &gt; BATTING</button>}</span>
            <b>{row.runs} <small>({row.balls})</small></b>
          </div>
          <MetricBar pct={row.bar_pct} color={row.bar_color} />
          <div className="metric-trail"><strong>Econ {row.econ}</strong><span>{row.wkts} wkt</span><span>{row.dots} dots</span></div>
        </div>
      );
    })}
  </div>
);

const PhaseCards = ({ rows, batting = false }) => {
  if (!rows?.available) return <EmptyState text={rows?.empty || 'Not enough balls for this split.'} />;
  return (
    <div className="split-grid three">
      {rows.rows.map((row) => (
        <div className="split-card" key={row.key}>
          <span>{row.label}</span>
          <small>ov {row.overs}</small>
          <b className={batting ? 'gold-value' : ''}>{batting ? row.runs : row.econ}</b>
          <em>{batting ? `${row.balls}b - SR ${row.sr}` : `${row.runs}r - ${row.wkts}w`}</em>
        </div>
      ))}
    </div>
  );
};

const SplitCards = ({ rows }) => {
  if (!rows?.available) return <EmptyState text={rows?.empty || 'Not enough balls for this split.'} />;
  return (
    <div className="split-grid two">
      {rows.rows.map((row) => (
        <div className="split-card" key={row.key}>
          <span>{row.label}</span>
          <b>{row.runs} <small>off {row.balls}</small></b>
          <strong>SR {row.sr}</strong>
          <em>{row.boundary_runs} boundary runs</em>
        </div>
      ))}
    </div>
  );
};

const HandCards = ({ rows }) => {
  if (!rows?.available) return <EmptyState text={rows?.empty || 'Not enough balls for this split.'} />;
  return (
    <div className="split-grid two">
      {rows.rows.map((row) => (
        <div className="split-card" key={row.key}>
          <span>{row.label}</span>
          <b>{row.econ} <small>econ</small></b>
          <em>{row.runs}r off {row.balls} - {row.wkts}w</em>
        </div>
      ))}
    </div>
  );
};

const WagonSpokes = ({ rows, color, bowling = false }) => {
  if (!rows?.available) return <EmptyState text={rows?.empty || 'No wagon-wheel data.'} />;
  const spokes = buildSpokes(rows.rows);
  return (
    <div className="wagon-wrap">
      <svg viewBox="0 0 100 100" width="240" height="240">
        <circle cx="50" cy="52" r="44" fill={bowling ? 'rgba(91,141,239,0.04)' : 'rgba(240,180,41,0.04)'} />
        <circle cx="50" cy="52" r="22" />
        {spokes.map((zone) => (
          <g key={zone.zone}>
            <line x1="50" y1="52" x2={zone.x2} y2={zone.y2} stroke={color} />
            <circle cx={zone.x2} cy={zone.y2} r="2.4" fill={color} />
            <text x={zone.lx} y={zone.ly}>{zone.label}</text>
          </g>
        ))}
        <circle cx="50" cy="52" r="3" className="center" />
      </svg>
      <p>{bowling ? 'Runs conceded by zone' : 'Runs by scoring zone'} - from wagon_zone</p>
    </div>
  );
};

const buildSpokes = (zones) => {
  const maxRuns = Math.max(...zones.map((zone) => zone.runs), 1);
  return zones.map((zone) => {
    const radius = 12 + (zone.runs / maxRuns) * (40 - 12);
    const radians = zone.angle * Math.PI / 180;
    const labelRadius = radius + 7;
    return {
      ...zone,
      x2: (50 + radius * Math.cos(radians)).toFixed(1),
      y2: (52 - radius * Math.sin(radians)).toFixed(1),
      lx: (50 + labelRadius * Math.cos(radians)).toFixed(1),
      ly: (52 - labelRadius * Math.sin(radians) + 1).toFixed(1),
    };
  });
};

const LineLengthHeatmap = ({ rows, batting = false }) => {
  if (!rows?.available) return <EmptyState text={rows?.empty || 'Line & length grid needs more tracked balls.'} />;
  const axes = rows.rows || { lines: [], lengths: [] };
  const cellMap = new Map((rows.cells || []).map((cell) => [`${cell.length}-${cell.line}`, cell]));
  return (
    <div className="heatmap-wrap">
      <div className="panel-title">{batting ? 'Strike rate' : 'Economy'} by line and length</div>
      <div className="heatmap-grid" style={{ gridTemplateColumns: `46px repeat(${axes.lines.length}, 1fr)` }}>
        <span />
        {axes.lines.map((line) => <span className="axis-label" key={line.key}>{line.label}</span>)}
        {axes.lengths.map((length) => (
          <React.Fragment key={length.key}>
            <span className="axis-label row">{length.label}</span>
            {axes.lines.map((line) => {
              const cell = cellMap.get(`${length.key}-${line.key}`);
              return (
                <span
                  key={`${length.key}-${line.key}`}
                  className="heat-cell"
                  style={{ background: cell ? heatColor(cell.metric, batting) : 'rgba(255,255,255,0.04)', color: cell && ((batting && cell.metric >= 170) || (!batting && cell.metric <= 6)) ? '#0a0c11' : undefined }}
                >
                  {cell?.balls ? cell.metric : ''}
                </span>
              );
            })}
          </React.Fragment>
        ))}
      </div>
      <div className={`heat-legend ${batting ? 'batting' : 'bowling'}`}><span>{batting ? 'Low' : 'Economical'}</span><i /><span>{batting ? 'High SR' : 'Expensive'}</span></div>
    </div>
  );
};

const heatColor = (metric, batting) => {
  if (batting) {
    if (metric >= 170) return 'rgba(182,242,74,0.6)';
    if (metric >= 120) return 'rgba(240,180,41,0.45)';
    return 'rgba(91,141,239,0.35)';
  }
  if (metric <= 6) return 'rgba(182,242,74,0.6)';
  if (metric <= 9) return 'rgba(240,180,41,0.45)';
  return 'rgba(229,72,77,0.45)';
};

const MetricBar = ({ pct, color }) => (
  <div className="metric-bar"><span style={{ width: `${Math.max(0, Math.min(100, pct || 0))}%`, background: color }} /></div>
);

const EmptyState = ({ text }) => <div className="scorecard-empty">{text}</div>;

export default MatchScorecardPage;
