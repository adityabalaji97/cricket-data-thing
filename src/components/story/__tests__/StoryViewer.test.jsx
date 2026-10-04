import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';

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
  it('moves with arrow keys and edge buttons, and keeps the hash on the current card', () => {
    render(<StoryViewer chapters={chapters(['a', 'b', 'c'])} fixtureLabel="MI v CSK" />);
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

  it('swipes through 4 cards per chapter and puts the rest below the current card', () => {
    const big = [
      { id: 'g', title: 'The ground', cards: ['g1', 'g2', 'g3', 'g4', 'g5', 'g6'].map(card) },
      { id: 't', title: 'The teams', cards: ['t1'].map(card) },
    ];
    render(<StoryViewer chapters={big} fixtureLabel="x" />);
    expect(screen.getByText('More in this chapter (2)')).toBeInTheDocument();
    expect(screen.getByText('chart g5')).toBeInTheDocument();
    expect(screen.getByText('chart g6')).toBeInTheDocument();
    ['g2', 'g3', 'g4', 't1'].forEach((next) => {
      fireEvent.keyDown(window, { key: 'ArrowRight' });
      expect(visibleTitle()).toBe(`Card ${next}`);
    });
    expect(screen.queryByText('More in this chapter (2)')).not.toBeInTheDocument();
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
    expect(visibleTitle()).toBe('Card t1');
  });

  it('mounts only the current card and its neighbours', () => {
    render(<StoryViewer chapters={chapters(['a', 'b', 'c', 'd'])} fixtureLabel="x" />);
    expect(screen.getByText('chart a')).toBeInTheDocument();
    expect(screen.getByText('chart b')).toBeInTheDocument();
    expect(screen.queryByText('chart c')).not.toBeInTheDocument();
  });

  it('keeps the sample line on the card and flags small samples', () => {
    const small = [{ id: 'one', title: 'One', cards: [{ ...card('a'), smallSample: true }] }];
    render(<StoryViewer chapters={small} fixtureLabel="x" />);
    expect(screen.getByText(/a sample/)).toBeInTheDocument();
    expect(screen.getByText(/small sample/)).toBeInTheDocument();
  });
});
