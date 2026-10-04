import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';

import StoryGrid from '../StoryGrid';

const chapters = [{
  id: 'ground',
  title: 'The ground',
  cards: [{
    id: 'a',
    title: 'Chasing sides have won 3 of 5 here',
    sample: '5 matches',
    info: <span>about</span>,
    render: () => <button type="button">Show details</button>,
  }],
}];

describe('StoryGrid', () => {
  it('opens the card on click, but not when a control inside the chart or the info button is used', () => {
    const onOpen = jest.fn();
    render(<StoryGrid chapters={chapters} onOpen={onOpen} />);
    fireEvent.click(screen.getByRole('button', { name: 'Show details' }));
    expect(onOpen).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: /Open Chasing sides/ }));
    expect(onOpen).toHaveBeenCalledTimes(1);
    expect(onOpen).toHaveBeenCalledWith('a');
    // The info button opens its sheet, not the card.
    fireEvent.click(screen.getByRole('button', { name: /About this chart/ }));
    expect(onOpen).toHaveBeenCalledTimes(1);
    expect(screen.getByText('about')).toBeInTheDocument();
  });
});
