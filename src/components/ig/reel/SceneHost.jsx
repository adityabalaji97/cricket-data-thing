import React from 'react';
import { Box } from '@mui/material';
import { drift, lift, teamTone, u } from './motion';
import { sceneFor } from './scenes';
import { Kicker } from './scenes/common';

/**
 * Draws the scenes live at t: the current one and, during the 0.1s overlap, the one leaving. Each sits in a full-frame
 * layer moved by the lift (computed from t), with its kicker. A scene's `team` overrides the Reel's for its colours.
 */
/** Reel-only kinds that hold still between beats (hero and hero_card bob, pick_one's tiles breathe, visuals drift). */
const DRIFT = new Set(['team_best', 'pool_count']);

const SceneHost = ({ spec, t }) => {
  const scenes = spec.scenes || [];
  return scenes.map((scene, i) => {
    const last = i === scenes.length - 1;
    if (t < scene.start - 0.1 || (!last && t > scene.end)) return null;
    const { o, dy } = lift(t, scene.start, scene.end, { last });
    if (o <= 0.001) return null;
    const Scene = sceneFor(scene.kind);
    const tone = teamTone(scene.team || spec.team);
    return (
      <Box key={`${scene.kind}-${scene.start}`} data-scene={scene.kind}
        sx={{ position: 'absolute', left: 0, top: 0, width: '100%', height: '100%', opacity: o, transform: `translateY(${u(dy)}px)`, willChange: 'transform, opacity' }}>
        {scene.kicker && <Kicker>{scene.kicker}</Kicker>}
        {DRIFT.has(scene.kind) ? (
          // Reel-only boards with no motion of their own between beats drift as the card visuals do (M7: 0.8s)
          <Box sx={{ position: 'absolute', inset: 0, transform: `translateY(${drift(t - scene.start)}px)`, willChange: 'transform' }}>
            <Scene scene={scene} t={t} tone={tone} spec={spec} />
          </Box>
        ) : <Scene scene={scene} t={t} tone={tone} spec={spec} />}
      </Box>
    );
  });
};

export default SceneHost;
