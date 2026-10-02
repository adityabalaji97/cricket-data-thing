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

export default PlayerGlance;
