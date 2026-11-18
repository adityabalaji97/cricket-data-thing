import HeroScene from './HeroScene';
import VisualScene, { PlaceholderScene, visualFor } from './VisualScene';
import { HeroCardScene, PickOneScene, PoolCountScene, TeamBestScene } from './RoundScenes';

/**
 * Reel scene kinds. Reel-only kinds are drawn at Reel sizes; every carousel visual kind (POST_VISUALS, VISUALS) plays
 * through VisualScene, with its own motion where it has one and the fallback otherwise. Anything else is a placeholder.
 */
export const SCENES = {
  hero: HeroScene,
  hero_card: HeroCardScene,
  team_best: TeamBestScene,
  pool_count: PoolCountScene,
  pick_one: PickOneScene,
};

export const sceneFor = (kind) => SCENES[kind] || (visualFor(kind) ? VisualScene : PlaceholderScene);
