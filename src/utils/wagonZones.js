export const SCORING_ZONE_LABELS = Object.freeze({
  1: 'Point',
  2: 'Cover',
  3: 'Long Off',
  4: 'Long On',
  5: 'Midwicket',
  6: 'Square Leg',
  7: 'Fine Leg',
  8: 'Behind',
});

export const SCORING_ZONE_VALUES = Object.freeze(
  Array.from({ length: 8 }, (_, index) => String(index + 1))
);

export const getScoringZoneLabel = (zone) => {
  const zoneNum = Number(zone);
  return SCORING_ZONE_LABELS[zoneNum] || `Zone ${zone}`;
};

export const normalizeScoringZone = (delivery) => {
  const rawZone = Number(delivery?.wagon_zone);
  if (Number.isFinite(rawZone) && rawZone >= 1 && rawZone <= 8) {
    return String(rawZone);
  }

  const x = Number(delivery?.wagon_x);
  const y = Number(delivery?.wagon_y);
  if (!Number.isFinite(x) || !Number.isFinite(y)) {
    return null;
  }

  const dx = x - 150;
  const dy = y - 150;
  if (dx === 0 && dy === 0) {
    return '1';
  }

  let theta = Math.atan2(dy, dx) + Math.PI / 2;
  if (theta < 0) theta += Math.PI * 2;
  const sector = Math.floor(theta / (Math.PI / 4)) + 1;
  return String(sector > 8 ? 1 : sector);
};
