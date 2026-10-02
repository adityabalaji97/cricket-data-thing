import React from 'react';
import TakeawayCard, { TakeawayStrip } from '../ui/TakeawayCard';

const MIN_BALLS = 60;
const PHASE_NAME = { powerplay: 'Powerplay', middle: 'Middle overs', death: 'Death' };

const sumPhases = (byPhase) => {
  if (!byPhase) return null;
  if (byPhase.overall) return byPhase.overall;
  const parts = ['powerplay', 'middle', 'death'].map((p) => byPhase[p]).filter(Boolean);
  const runs = parts.reduce((a, p) => a + (p.runs || 0), 0);
  const balls = parts.reduce((a, p) => a + (p.balls || 0), 0);
  return balls ? { runs, balls, strike_rate: (runs * 100) / balls } : null;
};

const sr = (v) => Math.round(Number(v) || 0);

/**
 * "At a glance" for a batter: the profile's answer in four cards, from data the page already
 * loaded (/player/{name}/stats). Every card names its sample; anything under 60 balls is skipped.
 */
const PlayerGlance = ({ stats }) => {
  const o = stats?.overall;
  const ps = stats?.phase_stats;
  if (!o || !ps) return null;
  const cards = [];

  cards.push(
    <TakeawayCard
      key="runs"
      highlight
      label="Runs · strike rate"
      value={o.runs ?? 0}
      unit={`at SR ${(o.strike_rate || 0).toFixed(1)}`}
      caption={`Average ${(o.average || 0).toFixed(1)} across ${o.matches || 0} innings.`}
      footnote={`${o.fifties || 0} fifties · ${o.hundreds || 0} hundreds`}
    />,
  );

  const phases = Object.entries(ps.overall || {})
    .filter(([key, v]) => PHASE_NAME[key] && (v?.balls || 0) >= MIN_BALLS);
  if (phases.length) {
    const totalBalls = phases.reduce((a, [, v]) => a + v.balls, 0);
    const [bestKey, best] = phases.reduce((a, b) => (b[1].strike_rate > a[1].strike_rate ? b : a));
    cards.push(
      <TakeawayCard
        key="phase"
        label="Best phase"
        value={PHASE_NAME[bestKey]}
        unit={`SR ${sr(best.strike_rate)}`}
        caption={`${Math.round((best.balls * 100) / totalBalls)}% of his balls come here; boundary ${(best.boundary_percentage || 0).toFixed(1)}%.`}
        footnote={`${best.balls} balls`}
      />,
    );
  }

  const pace = sumPhases(ps.pace);
  const spin = sumPhases(ps.spin);
  if (pace?.balls >= MIN_BALLS && spin?.balls >= MIN_BALLS) {
    const faster = pace.strike_rate >= spin.strike_rate ? 'pace' : 'spin';
    cards.push(
      <TakeawayCard
        key="kind"
        label="Pace v spin"
        value={`SR ${sr(faster === 'pace' ? pace.strike_rate : spin.strike_rate)}`}
        unit={`v ${faster}`}
        caption={`SR ${sr(faster === 'pace' ? spin.strike_rate : pace.strike_rate)} v ${faster === 'pace' ? 'spin' : 'pace'}.`}
        footnote={`${pace.balls} balls v pace · ${spin.balls} v spin`}
      />,
    );
  }

  const types = Object.entries(ps.bowling_types || {})
    .map(([type, byPhase]) => [type, sumPhases(byPhase)])
    .filter(([, v]) => v && v.balls >= MIN_BALLS);
  if (types.length >= 2) {
    const [worstType, worst] = types.reduce((a, b) => (b[1].strike_rate < a[1].strike_rate ? b : a));
    cards.push(
      <TakeawayCard
        key="weak"
        label="Toughest bowling type"
        value={worstType}
        unit={`SR ${sr(worst.strike_rate)}`}
        caption={`His slowest scoring against any bowling type with ${MIN_BALLS}+ balls.`}
        footnote={`${worst.balls} balls`}
      />,
    );
  }

  return <TakeawayStrip columns={4}>{cards}</TakeawayStrip>;
};

const PHASE_ORDER = ['powerplay', 'middle', 'death'];
const fmt1 = (v) => (v == null || Number.isNaN(Number(v)) ? '–' : Number(v).toFixed(1));

/**
 * "At a glance" for a bowler, from /player/{name}/bowling_stats: wickets & economy, the phase where
 * wickets come fastest, control (dots v boundaries), and left- v right-handers. 60+ balls each.
 */
export const BowlerGlance = ({ stats }) => {
  const o = stats?.overall;
  const ps = stats?.phase_stats;
  if (!o) return null;
  const cards = [];

  cards.push(
    <TakeawayCard
      key="wkts"
      highlight
      label="Wickets · economy"
      value={o.wickets ?? 0}
      unit={`at economy ${fmt1(o.economy_rate)}`}
      caption={`Average ${fmt1(o.bowling_average)}, a wicket every ${fmt1(o.bowling_strike_rate)} balls.`}
      footnote={`${o.matches || 0} matches · ${o.balls || 0} balls`}
    />,
  );

  const phases = PHASE_ORDER
    .map((key) => [key, ps?.[key]])
    .filter(([, v]) => v && (v.balls || 0) >= MIN_BALLS && (v.wickets || 0) > 0);
  if (phases.length) {
    const [key, best] = phases.reduce((a, b) => (b[1].bowling_strike_rate < a[1].bowling_strike_rate ? b : a));
    const share = o.wickets ? Math.round((best.wickets * 100) / o.wickets) : 0;
    cards.push(
      <TakeawayCard
        key="phase"
        label="Wicket phase"
        value={PHASE_NAME[key]}
        unit={`a wicket every ${fmt1(best.bowling_strike_rate)} balls`}
        caption={`${best.wickets} wickets (${share}% of his total) at economy ${fmt1(best.economy)}.`}
        footnote={`${best.balls} balls`}
      />,
    );
  }

  cards.push(
    <TakeawayCard
      key="control"
      label="Control"
      value={`${fmt1(o.dot_percentage)}%`}
      unit="dot balls"
      caption={`Boundaries off ${fmt1(o.boundary_percentage)}% of balls.`}
      footnote={`${o.balls || 0} balls`}
    />,
  );

  const lhb = stats?.batter_handedness?.LHB?.overall;
  const rhb = stats?.batter_handedness?.RHB?.overall;
  if (lhb?.balls >= MIN_BALLS && rhb?.balls >= MIN_BALLS) {
    const better = lhb.economy <= rhb.economy ? ['left', lhb, 'right', rhb] : ['right', rhb, 'left', lhb];
    cards.push(
      <TakeawayCard
        key="hand"
        label="Left v right"
        value={`Econ ${fmt1(better[1].economy)}`}
        unit={`v ${better[0]}-handers`}
        caption={`Economy ${fmt1(better[3].economy)} v ${better[2]}-handers; a wicket every ${fmt1(better[1].bowling_strike_rate)} v ${fmt1(better[3].bowling_strike_rate)} balls.`}
        footnote={`${lhb.balls} balls v LHB · ${rhb.balls} v RHB`}
      />,
    );
  }

  return <TakeawayStrip columns={4}>{cards}</TakeawayStrip>;
};

export default PlayerGlance;
