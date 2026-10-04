import { createContext, useContext } from 'react';

/**
 * Lets a card's visual open another card (the "At a glance" tiles). The story viewer jumps to
 * it; the desktop grid opens the viewer on it. Outside either, tiles do nothing.
 */
const StoryNav = createContext({ openCard: null });

export const useStoryNav = () => useContext(StoryNav);
export default StoryNav;
