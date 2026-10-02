import React, { useState } from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import axios from 'axios';
import CompetitionFilter from '../CompetitionFilter';

jest.mock('axios', () => ({
  __esModule: true,
  default: { get: jest.fn() },
}));

const Harness = ({ onChange }) => {
  const [value, setValue] = useState({ leagues: [], international: true, topTeams: 20 });
  return (
    <CompetitionFilter
      value={value}
      onFilterChange={(next) => { setValue(next); onChange(next); }}
    />
  );
};

describe('CompetitionFilter', () => {
  beforeEach(() => {
    axios.get.mockResolvedValue({
      data: {
        leagues: [
          { value: 'Indian Premier League', label: 'Indian Premier League' },
          { value: 'Big Bash League', label: 'Big Bash League' },
        ],
      },
    });
  });

  it('replaces "All Leagues" with a single picked league', async () => {
    const onChange = jest.fn();
    render(<Harness onChange={onChange} />);
    const input = await screen.findByRole('combobox');
    fireEvent.mouseDown(input);
    fireEvent.click(await screen.findByText('Indian Premier League'));

    await waitFor(() => {
      expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ leagues: ['Indian Premier League'] }));
    });
    expect(screen.queryByText('All Leagues', { selector: '.MuiChip-label' })).not.toBeInTheDocument();
  });
});
