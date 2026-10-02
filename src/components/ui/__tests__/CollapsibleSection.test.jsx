import React from 'react';
import { act, fireEvent, render, screen } from '@testing-library/react';

import CollapsibleSection, { openSection } from '../CollapsibleSection';

beforeAll(() => {
  window.HTMLElement.prototype.scrollIntoView = jest.fn();
  global.requestAnimationFrame = (cb) => cb();
});

describe('CollapsibleSection', () => {
  it('does not mount children until first opened, then keeps them mounted', () => {
    let mounts = 0;
    const Child = () => { React.useEffect(() => { mounts += 1; }, []); return <div>body</div>; };
    render(<CollapsibleSection id="s1" title="Matchups" takeaway="Bumrah owns Kohli"><Child /></CollapsibleSection>);

    expect(screen.queryByText('body')).not.toBeInTheDocument();
    expect(screen.getByText('Bumrah owns Kohli')).toBeInTheDocument();

    const header = screen.getByRole('button', { name: /Matchups/ });
    fireEvent.click(header);
    expect(screen.getByText('body')).toBeInTheDocument();
    expect(header).toHaveAttribute('aria-expanded', 'true');

    fireEvent.click(header); // close
    fireEvent.click(header); // re-open
    expect(mounts).toBe(1);
  });

  it('mounts immediately when defaultOpen', () => {
    render(<CollapsibleSection id="s2" title="Overview" defaultOpen><div>body</div></CollapsibleSection>);
    expect(screen.getByText('body')).toBeInTheDocument();
  });

  it('opens via openSection()', () => {
    render(<CollapsibleSection id="s3" title="Impact"><div>impact body</div></CollapsibleSection>);
    expect(screen.queryByText('impact body')).not.toBeInTheDocument();
    act(() => openSection('s3'));
    expect(screen.getByText('impact body')).toBeInTheDocument();
  });
});
