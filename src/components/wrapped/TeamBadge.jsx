import React from 'react';
import CondensedName from '../common/CondensedName';

/**
 * Small badge showing abbreviated team name
 */
const TeamBadge = ({ team, size = 'small' }) => {
  if (!team) return null;
  
  const sizeStyles = {
    small: {
      fontSize: '9px',
      padding: '1px 4px',
    },
    medium: {
      fontSize: '10px',
      padding: '2px 6px',
    }
  };
  
  const style = sizeStyles[size] || sizeStyles.small;
  
  return (
    <CondensedName
      name={team}
      type="team"
      component="span"
      style={{
        backgroundColor: 'rgba(255, 255, 255, 0.1)',
        color: '#888',
        borderRadius: '3px',
        fontWeight: 500,
        letterSpacing: '0.5px',
        whiteSpace: 'nowrap',
        ...style
      }}
    />
  );
};

export default TeamBadge;
