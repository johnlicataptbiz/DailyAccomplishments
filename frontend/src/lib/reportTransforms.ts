import type { BulletItem, ProofEntry, TodayReport } from '../types/report';

export function candidateReportPaths(date: string): string[] {
  return [
    `/reports/${date}/ActivityReport-${date}.json`,
    `/ActivityReport-${date}.json`,
  ];
}

function parseHHMM(value?: string): number {
  if (!value) return 0;
  const match = value.match(/\b(\d{1,2}):(\d{2})\b/);
  if (!match) return 0;
  const hours = Number(match[1]);
  const minutes = Number(match[2]);
  if (Number.isNaN(hours) || Number.isNaN(minutes)) return 0;
  return hours * 60 + minutes;
}

export function buildBulletItems(report: TodayReport): BulletItem[] {
  const accomplishments = report.accomplishments_today ?? [];

  const deepWorkProof: ProofEntry[] =
    report.deep_work?.map((entry, idx) => ({
      id: `deep-${idx}`,
      title: entry.label || entry.category || 'Deep work',
      durationMinutes: entry.minutes ?? 0,
      timeRange: entry.start && entry.end ? `${entry.start}-${entry.end}` : undefined,
      category: entry.category,
      label: entry.label,
    })) ?? [];

  const focusMinutes = parseHHMM(report.overview?.focus_time);

  return accomplishments.map((text, idx) => ({
    id: `bullet-${idx}`,
    title: text,
    durationMinutes: idx === 0 ? focusMinutes : 0,
    category: undefined,
    proof: deepWorkProof,
    source: 'report',
  }));
}
