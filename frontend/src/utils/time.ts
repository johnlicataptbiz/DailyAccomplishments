export function parseDurationToMinutes(duration: string | number | undefined): number {
  if (typeof duration === 'number') return duration;
  if (!duration) return 0;

  if (duration.includes(':')) {
    const parts = duration.split(':').map((p) => Number(p));
    if (parts.length === 2 && parts.every((p) => !Number.isNaN(p))) {
      return parts[0] * 60 + parts[1];
    }
  }

  const match = /(?:(\d+)\s*h)?\s*(\d{1,2})?:?(\d{2})?/.exec(duration.trim());
  if (!match) return 0;

  const hours = Number(match[1] || match[2] || 0);
  const minutes = Number(match[3] || (match[2] && !match[1] ? match[2] : 0));
  return hours * 60 + minutes;
}

export function formatMinutes(totalMinutes: number): string {
  if (!Number.isFinite(totalMinutes) || totalMinutes <= 0) return '0m';
  const hours = Math.floor(totalMinutes / 60);
  const minutes = Math.round(totalMinutes % 60);
  if (hours === 0) return `${minutes}m`;
  if (minutes === 0) return `${hours}h`;
  return `${hours}h ${minutes}m`;
}

export function formatTimeRange(start?: string, end?: string): string | undefined {
  if (!start && !end) return undefined;
  if (start && end) return `${start}–${end}`;
  return start || end;
}
