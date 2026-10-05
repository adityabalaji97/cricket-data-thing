import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';

// axios ships ES modules Jest doesn't transform; the viewer only posts through it on a tap.
jest.mock('axios', () => ({ post: jest.fn(), get: jest.fn() }));

import StoryViewer from '../StoryViewer';
import { toStoryCard } from '../visuals';

const card = (id) => ({ id, title: `Card ${id}`, sample: `${id} sample`, render: () => <div>{`chart ${id}`}</div> });
const chapters = (ids) => [
  { id: 'one', title: 'One', cards: ids.filter((i) => i < 'c').map(card) },
  { id: 'two', title: 'Two', cards: ids.filter((i) => i >= 'c').map(card) },
].filter((c) => c.cards.length);

const visibleTitle = () => screen.getAllByRole('heading', { level: 2 })
  .find((h) => h.closest('[aria-hidden="true"]') === null).textContent;

beforeEach(() => {
  window.history.replaceState(null, '', '/venue?story=1');
});

describe('StoryViewer', () => {
  it('moves between chapters with arrow keys and edge buttons, and keeps the hash on the lead card', () => {
    const three = ['a', 'b', 'c'].map((id) => ({ id: `ch-${id}`, title: id, cards: [card(id)] }));
    render(<StoryViewer chapters={three} fixtureLabel="MI v CSK" />);
    expect(visibleTitle()).toBe('Card a');
    fireEvent.keyDown(window, { key: 'ArrowRight' });
    expect(visibleTitle()).toBe('Card b');
    expect(window.location.hash).toBe('#b');
    fireEvent.click(screen.getByRole('button', { name: 'Next card' }));
    expect(visibleTitle()).toBe('Card c');
    fireEvent.click(screen.getByRole('button', { name: 'Previous card' }));
    expect(visibleTitle()).toBe('Card b');
  });

  it('opens a deep-linked card that arrives after the first render', () => {
    window.history.replaceState(null, '', '/venue?story=1#c');
    const { rerender } = render(<StoryViewer chapters={chapters(['a'])} fixtureLabel="x" />);
    expect(visibleTitle()).toBe('Card a');
    expect(window.location.hash).toBe('#c'); // not overwritten while the card is pending
    rerender(<StoryViewer chapters={chapters(['a', 'b', 'c'])} fixtureLabel="x" />);
    expect(visibleTitle()).toBe('Card c');
  });

  it('stays on the same card when earlier cards load later', () => {
    window.history.replaceState(null, '', '/venue?story=1#c');
    const { rerender } = render(<StoryViewer chapters={chapters(['c'])} fixtureLabel="x" />);
    expect(visibleTitle()).toBe('Card c');
    rerender(<StoryViewer chapters={chapters(['a', 'b', 'c'])} fixtureLabel="x" />);
    expect(visibleTitle()).toBe('Card c');
  });

  it('swipes between chapters and scrolls the rest of each chapter below its lead card', () => {
    const big = [
      { id: 'g', title: 'The ground', cards: ['g1', 'g2', 'g3'].map(card) },
      { id: 't', title: 'The teams', cards: ['t1', 't2'].map(card) },
      { id: 'p', title: 'The players', cards: ['p1'].map(card) },
    ];
    render(<StoryViewer chapters={big} fixtureLabel="x" />);
    expect(screen.getByText('Scroll for 2 more')).toBeInTheDocument();
    expect(screen.getByText('chart g3')).toBeInTheDocument();
    // One progress segment per chapter.
    expect(screen.getByLabelText('Chapter 1 of 3')).toBeInTheDocument();
    fireEvent.keyDown(window, { key: 'ArrowRight' });
    expect(visibleTitle()).toBe('Card t1');
    expect(screen.getByLabelText('Chapter 2 of 3')).toBeInTheDocument();
    fireEvent.keyDown(window, { key: 'ArrowRight' });
    expect(visibleTitle()).toBe('Card p1');
    expect(screen.queryByText(/Scroll for/)).not.toBeInTheDocument();
  });

  it('renders a live panel at its own height below the chapter lead', () => {
    const panel = { id: 'matrix', panel: true, title: 'Every batter v bowler match-up', render: () => <div>matrix body</div> };
    render(<StoryViewer chapters={[{ id: 'l', title: 'Line-ups', cards: [card('x1'), panel] }]} fixtureLabel="x" />);
    expect(screen.getByText('matrix body')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Every batter v bowler match-up' })).toBeInTheDocument();
  });

  it('opens a link to an extra card on its chapter', () => {
    window.history.replaceState(null, '', '/venue?story=1#g6');
    const big = [{ id: 'g', title: 'The ground', cards: ['g1', 'g2', 'g3', 'g4', 'g5', 'g6'].map(card) }];
    render(<StoryViewer chapters={big} fixtureLabel="x" />);
    expect(visibleTitle()).toBe('Card g1');
    expect(document.getElementById('story-extra-g6')).not.toBeNull();
  });

  it('opens a card from an At a glance tile', () => {
    const glance = toStoryCard({
      id: 'glance', title: 'Par about 212', sample: 's', visual: 'tiles',
      payload: { tiles: [{ card: 't1', label: 'Head to head', value: '4–1', sub: 'CSK lead' }] },
    }, { isMobile: true });
    const story = [
      { id: 'glance', title: 'At a glance', cards: [glance] },
      { id: 't', title: 'The teams', cards: ['t0', 't1'].map(card) },
    ];
    render(<StoryViewer chapters={story} fixtureLabel="x" />);
    fireEvent.click(screen.getByRole('button', { name: /Head to head: 4–1, CSK lead/ }));
    // t1 sits below the teams chapter's lead: the viewer opens that chapter and scrolls to it.
    expect(visibleTitle()).toBe('Card t0');
    expect(document.getElementById('story-extra-t1')).not.toBeNull();
  });

  it('mounts the current chapter and the neighbouring chapter leads only', () => {
    // Chapter one is a, b; chapter two is c, d.
    render(<StoryViewer chapters={chapters(['a', 'b', 'c', 'd'])} fixtureLabel="x" />);
    expect(screen.getByText('chart a')).toBeInTheDocument();
    expect(screen.getByText('chart b')).toBeInTheDocument(); // below the lead, same chapter
    expect(screen.getByText('chart c')).toBeInTheDocument(); // next chapter's lead, preloaded
    expect(screen.queryByText('chart d')).not.toBeInTheDocument();
  });

  it('keeps the sample line on the card and flags small samples', () => {
    const small = [{ id: 'one', title: 'One', cards: [{ ...card('a'), smallSample: true }] }];
    render(<StoryViewer chapters={small} fixtureLabel="x" />);
    expect(screen.getByText(/a sample/)).toBeInTheDocument();
    expect(screen.getByText(/small sample/)).toBeInTheDocument();
  });
});
