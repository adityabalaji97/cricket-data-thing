// condenseName("Aiden Markram") → "A Markram"
// condenseName("KL Rahul") → "KL Rahul" (already short)
export const condenseName = (name) => {
  if (!name) return '';
  const parts = name.trim().split(/\s+/);
  if (parts.length <= 1) return name;
  if (parts[0].length <= 3 && parts[0] === parts[0].toUpperCase()) return name;
  return `${parts[0][0]} ${parts.slice(1).join(' ')}`;
};

// Form border colors: HOT→green, COLD→red, NEUTRAL→orange
export const getFormBorderColor = (formMeta) => {
  if (!formMeta) return 'transparent';
  switch (formMeta.label) {
    case 'HOT': return '#4caf50';
    case 'COLD': return '#f44336';
    case 'NEUTRAL': return '#ff9800';
    default: return 'transparent';
  }
};
