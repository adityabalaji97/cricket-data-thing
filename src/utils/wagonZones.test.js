import {
  getMirroredZone,
  getScoringZoneLabel,
  isLeftHandBat,
} from './wagonZones';

describe('wagonZones handedness labeling', () => {
  it('returns the RHB label set by default', () => {
    expect(getScoringZoneLabel('1')).toBe('Fine Leg');
    expect(getScoringZoneLabel('2')).toBe('Square Leg');
    expect(getScoringZoneLabel('8')).toBe('Behind');
  });

  it('mirrors labels for LHB across the vertical 12-6 axis', () => {
    expect(getScoringZoneLabel('1', 'LHB')).toBe('Point');
    expect(getScoringZoneLabel('2', 'LHB')).toBe('Cover');
    expect(getScoringZoneLabel('3', 'LHB')).toBe('Long Off');
    expect(getScoringZoneLabel('4', 'LHB')).toBe('Long On');
    expect(getScoringZoneLabel('8', 'LHB')).toBe('Behind');
  });

  it('provides helper semantics for mirrored zone ids', () => {
    expect(getMirroredZone(1)).toBe(7);
    expect(getMirroredZone(2)).toBe(6);
    expect(getMirroredZone(4)).toBe(4);
    expect(getMirroredZone(8)).toBe(8);
  });

  it('detects left-handed bat input values', () => {
    expect(isLeftHandBat('LHB')).toBe(true);
    expect(isLeftHandBat('left')).toBe(true);
    expect(isLeftHandBat('RHB')).toBe(false);
    expect(isLeftHandBat(null)).toBe(false);
  });
});
