const toNumericValues = (values = []) =>
  values
    .map((value) => Number(value))
    .filter((value) => Number.isFinite(value));

const roundDomainValue = (value) => Math.round(value * 1000) / 1000;

export const trimOutliers = (values = [], stdDevThreshold = 2) => {
  const numericValues = toNumericValues(values);
  if (numericValues.length < 3) return numericValues;

  const mean = numericValues.reduce((sum, value) => sum + value, 0) / numericValues.length;
  const variance = numericValues.reduce((sum, value) => sum + (value - mean) ** 2, 0) / numericValues.length;
  const stdDev = Math.sqrt(variance);

  if (!Number.isFinite(stdDev) || stdDev === 0) return numericValues;

  const maxDeviation = stdDevThreshold * stdDev;
  const trimmed = numericValues.filter((value) => Math.abs(value - mean) <= maxDeviation);

  return trimmed.length >= 2 ? trimmed : numericValues;
};

export const getAutoscaledDomain = (
  values = [],
  {
    paddingRatio = 0.1,
    stdDevThreshold = 2,
    clampMin,
    clampMax,
    minRange = 1,
    fallbackDomain = [0, 1],
  } = {},
) => {
  const numericValues = toNumericValues(values);
  if (numericValues.length === 0) {
    return fallbackDomain;
  }

  const trimmedValues = trimOutliers(numericValues, stdDevThreshold);
  let min = Math.min(...trimmedValues);
  let max = Math.max(...trimmedValues);

  if (min === max) {
    const delta = Math.max(Math.abs(min) * paddingRatio, minRange / 2, 0.5);
    min -= delta;
    max += delta;
  }

  const range = Math.max(max - min, minRange);
  const padding = range * paddingRatio;

  let domainMin = min - padding;
  let domainMax = max + padding;

  if (Number.isFinite(clampMin)) {
    domainMin = Math.max(clampMin, domainMin);
  }

  if (Number.isFinite(clampMax)) {
    domainMax = Math.min(clampMax, domainMax);
  }

  if (domainMin >= domainMax) {
    const center = (min + max) / 2;
    domainMin = center - minRange / 2;
    domainMax = center + minRange / 2;
  }

  return [roundDomainValue(domainMin), roundDomainValue(domainMax)];
};

