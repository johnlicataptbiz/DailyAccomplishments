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
 * Converts accomplishments_today into editable bullets with proof entries from deep_work.
 */
export function buildBulletItems(report: TodayReport): BulletItem[] {
  const accomplishments = report.accomplishments_today ?? [];

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

  // Extract focus time from overview
  const defaultMinutes = report.overview?.focus_time
    ? parseDurationToMinutes(report.overview.focus_time)
    : 0;

  // Convert accomplishments to bullet items
  const bullets = accomplishments.map((text, idx) => ({
    id: `bullet-${idx}`,
    title: text,
    durationMinutes: 0, // Keep editable; can be improved with parsing later
    category: undefined,
    proof: deepProof,
    source: 'report' as const,
  }));

  // If we have bullets and focus time, assign the focus time to the first bullet
  if (bullets.length > 0 && defaultMinutes > 0) {
    bullets[0] = {
      ...bullets[0],
      durationMinutes: defaultMinutes,
    };
  }

  return bullets;
}
