import type { BulletItem, ProofEntry, TodayReport } from '../types/report';
import { parseDurationToMinutes } from '../utils/time';

/**
 * Generate candidate paths for fetching a report for a given date.
 * Matches the documented fetch order: try /reports/<DATE>/ActivityReport-<DATE>.json first,
 * then fallback to /ActivityReport-<DATE>.json
 */
export function candidateReportPaths(date: string): string[] {
  return [
    `/reports/${date}/ActivityReport-${date}.json`,
    `/ActivityReport-${date}.json`,
  ];
}

/**
 * Build bullet items from a TodayReport.
 * 
 * Strategy (in priority order):
 * 1. Use headline_bullets if present (schema v2)
 * 2. Use accomplishments_today if present (schema v1)
 * 3. Generate a default bullet from focus time or deep work
 * 4. Generate a placeholder bullet
 * 
 * This ensures the UI never shows "No bullets available" unless user explicitly deletes all.
 */
export function buildBulletItems(report: TodayReport): BulletItem[] {
  // Build proof entries primarily from deep_work
  const deepProof: ProofEntry[] =
    report.deep_work?.map((entry, idx) => ({
      id: `deep-${idx}`,
      title: entry.label || entry.category || 'Deep work',
      durationMinutes: entry.minutes ?? 0,
      timeRange: entry.start && entry.end ? `${entry.start}-${entry.end}` : undefined,
      category: entry.category,
      label: entry.label,
    })) ?? [];

  // Extract focus time from overview (handle both v1 string and v2 number formats)
  const focusMinutes = 
    typeof report.overview?.focus_time === 'number'
      ? report.overview.focus_time
      : report.overview?.focus_time
        ? parseDurationToMinutes(report.overview.focus_time)
        : 0;

  // Try headline_bullets first (schema v2)
  const headlines = (report as any).headline_bullets ?? report.accomplishments_today ?? [];

  // 1) If accomplishments/headlines exist, use them
  if (headlines.length > 0) {
    const bullets: BulletItem[] = headlines.map((text: string, idx: number) => ({
      id: `bullet-${idx}`,
      title: text,
      durationMinutes: 0,
      category: undefined,
      proof: deepProof,
      source: 'report',
    }));

    // Put focus time on first bullet as a sensible default
    if (focusMinutes > 0) {
      bullets[0] = { ...bullets[0], durationMinutes: focusMinutes };
    }
    return bullets;
  }

  // 2) If no accomplishments, generate a starter bullet from focus time or proof
  const fallbackTitle =
    focusMinutes > 0
      ? `Focused work for ${Math.floor(focusMinutes / 60)}h ${focusMinutes % 60}m`
      : deepProof.length > 0
        ? `Worked on ${deepProof[0].title}`
        : 'Add your first highlight';

  return [
    {
      id: 'bullet-0',
      title: fallbackTitle,
      durationMinutes: focusMinutes > 0 ? focusMinutes : 0,
      category: undefined,
      proof: deepProof,
      source: 'report',
    },
  ];
}
