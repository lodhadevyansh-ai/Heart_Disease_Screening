/**
 * Clinical and User-facing Data Formatters.
 */

export function formatDateTime(isoString) {
  if (!isoString) return '—';
  try {
    let str = String(isoString).trim();
    // If string is an ISO format without timezone offset, server generates all in UTC,
    // so append 'Z' to prevent browser from misinterpreting it as naive local time.
    if (str.includes('T') && !str.endsWith('Z') && !str.slice(10).includes('+') && !str.slice(10).includes('-')) {
      str = str + 'Z';
    } else if (!str.includes('T') && str.includes(' ')) {
      str = str.replace(' ', 'T') + 'Z';
    }
    const d = new Date(str);
    if (isNaN(d.getTime())) return isoString;
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(d);
  } catch {
    return isoString;
  }
}

export function formatProbability(prob) {
  if (prob === null || prob === undefined || isNaN(prob)) return '—';
  return `${(Number(prob) * 100).toFixed(1)}%`;
}

export function formatScore(score) {
  if (score === null || score === undefined || isNaN(score)) return '—';
  return Number(score).toFixed(3);
}

export function formatBloodPressure(sys, dia) {
  if (sys === null || sys === undefined || dia === null || dia === undefined) {
    if (sys) return `${sys} / — mmHg`;
    if (dia) return `— / ${dia} mmHg`;
    return 'Not measured';
  }
  return `${sys}/${dia} mmHg`;
}

export function formatVital(value, unit = '') {
  if (value === null || value === undefined || value === '') {
    return 'Not measured';
  }
  return `${value}${unit ? ' ' + unit : ''}`;
}

export function formatAnginaClassification(angina) {
  const map = {
    typical_angina: 'Typical Angina (Definite)',
    atypical_angina: 'Atypical Angina (Probable)',
    non_anginal: 'Non-Anginal Chest Pain',
    none: 'Asymptomatic / None',
  };
  return map[angina] || angina || 'Not assessed';
}
