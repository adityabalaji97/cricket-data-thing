import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';

import StoryViewer from '../StoryViewer';

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
