/**
 * Schema Version 2 - Canonical Frontend Report Contract
 * 
 * This is the stable interface the UI relies on. Backend generators can include
 * additional fields in `raw`, but the UI should only depend on these fields.
 */

export type ReportSchemaVersion = 2;

export type ProofSource =
  | 'deep_work'
  | 'timeline'
  | 'apps'
  | 'meetings'
  | 'manual';

export interface ProofEntry {
  id: string;
  source: ProofSource;
  title: string;
  durationMinutes?: number;
  timeRange?: string;        // "09:10-10:05"
  category?: string;         // "Coding"
  label?: string;            // "Implement Today Brief"
  url?: string;
}

export interface BulletItemV2 {
  id: string;
  title: string;
  durationMinutes: number;
  category?: string;
  proof: ProofEntry[];
  source: 'report' | 'user' | 'merged';
  hidden?: boolean;
}

export interface ReportOverview {
  date: string;              // "2025-12-17"
  focusMinutes?: number;     // normalized number, avoid HH:MM in UI contract
  meetingMinutes?: number;
  activeMinutes?: number;
  coverageMinutes?: number;
  notes?: string;
}

export interface TodayReportV2 {
  schema_version: ReportSchemaVersion;

  overview: ReportOverview;

  // This is the only source of truth for headlines in the UI.
  headline_bullets: string[];

  // These are the receipts the UI can show in drawers, filters, trends.
  proof: {
    deep_work?: ProofEntry[];
    timeline?: ProofEntry[];
    apps?: ProofEntry[];
    meetings?: ProofEntry[];
  };

  // Optional, for debugging and backwards compatibility.
  raw?: Record<string, unknown>;
}
