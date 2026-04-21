import React from 'react';
import { Tooltip } from '@mui/material';
import { condenseName } from '../../utils/playerNameUtils';
import { getTeamAbbr, TEAM_ABBREVIATIONS } from '../../utils/teamAbbreviations';

// Reverse lookup: abbreviation → full team name
const ABBR_TO_FULL = {};
Object.entries(TEAM_ABBREVIATIONS).forEach(([full, abbr]) => {
  if (!ABBR_TO_FULL[abbr]) {
    ABBR_TO_FULL[abbr] = full;
  }
});

const CondensedName = ({ name, type = 'player', style, className, component: Component = 'span', ...rest }) => {
  const normalizedName = String(name || '').trim();
  if (!normalizedName) return null;

  let displayName;
  let tooltipText;

  if (type === 'team') {
    const fullNameFromAbbr = ABBR_TO_FULL[normalizedName];
    displayName = getTeamAbbr(fullNameFromAbbr || normalizedName);
    // Full name input: "Mumbai Indians" -> "MI" with tooltip "Mumbai Indians"
    // Abbreviation input: "MI" -> "MI" with tooltip "Mumbai Indians" when known.
    tooltipText = displayName !== normalizedName ? normalizedName : (fullNameFromAbbr || '');
  } else {
    displayName = condenseName(normalizedName);
    // Show full name in tooltip if it was condensed
    tooltipText = displayName !== normalizedName ? normalizedName : '';
  }

  if (!tooltipText) {
    return <Component style={style} className={className} {...rest}>{displayName}</Component>;
  }

  return (
    <Tooltip title={tooltipText} arrow enterDelay={300} enterTouchDelay={100}>
      <Component style={style} className={className} {...rest}>{displayName}</Component>
    </Tooltip>
  );
};

export default CondensedName;
