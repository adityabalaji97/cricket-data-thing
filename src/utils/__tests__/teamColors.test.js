import { getTeamColor, getTeamPalette, getTeamSecondary, textOn } from '../teamColors';
import PALETTE from '../teamPalette.json';

describe('team palette', () => {
  test('full names, old names and IPL/international abbreviations resolve to one team', () => {
    expect(getTeamColor('Royal Challengers Bangalore')).toBe(getTeamColor('Royal Challengers Bengaluru'));
    expect(getTeamColor('Kings XI Punjab')).toBe(getTeamColor('PBKS'));
    expect(getTeamColor('csk')).toBe(PALETTE.teams['Chennai Super Kings'].primary);
    expect(getTeamColor('Chennai Super Kings / CSK')).toBe(getTeamColor('CSK'));
  });

  test('league teams beyond the IPL are covered, with a trim colour', () => {
    expect(getTeamPalette('Perth Scorchers')).toMatchObject({ league: 'BBL' });
    expect(getTeamSecondary("Durban's Super Giants")).toMatch(/^#[0-9A-F]{6}$/);
    expect(getTeamColor('Durban Super Giants')).toBe(getTeamColor("Durban's Super Giants"));
    expect(getTeamColor('Warwickshire')).not.toBeNull();
  });

  test('SCO stays Scotland (league codes collide, so they are not aliases)', () => {
    expect(getTeamPalette('SCO').name).toBe('Scotland');
  });

  test('unknown teams give null', () => {
    expect(getTeamColor('Not A Team')).toBeNull();
    expect(getTeamSecondary(null)).toBeNull();
  });

  test('every colour is a 6-digit hex and every alias points at a team', () => {
    Object.values(PALETTE.teams).forEach(({ primary, secondary }) => {
      expect(primary).toMatch(/^#[0-9A-F]{6}$/);
      expect(secondary).toMatch(/^#[0-9A-F]{6}$/);
    });
    Object.values(PALETTE.aliases).forEach((name) => expect(PALETTE.teams[name]).toBeDefined());
  });

  test('India and Afghanistan are no longer the same blue', () => {
    expect(getTeamColor('India')).not.toBe(getTeamColor('Afghanistan'));
    expect(textOn(getTeamColor('Sunrisers Hyderabad'))).toBe('#0a0c11');
  });
});
