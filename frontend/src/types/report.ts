export interface Overview {
  // Schema v2 fields (numeric)
  date?: string;
  focusMinutes?: number;
  meetingMinutes?: number;
  activeMinutes?: number;
  coverageMinutes?: number;
  // Schema v1 fields (string HH:MM format) - kept for backwards compatibility
  active_time?: string;
  focus_time?: string | number;  // Can be string (v1) or number (v2)
  meetings_time?: string;
  coverage_time?: string;
  coverage_window?: string;
  appointments?: number;
  projects_count?: number;
}

export interface DeepWorkEntry {
  start?: string;
  end?: string;
  minutes?: number;
  category?: string;
  label?: string;
}

export interface TimelineEntry {
  start?: string;
  end?: string;
  minutes?: number;
  seconds?: number;
  category?: string;
  label?: string;
  app?: string;
  details?: string;
  type?: string;
}

export interface HourlyFocusEntry {
  hour: number;
  time: string;
  pct?: string;
}

export interface DeepWorkBlock {
  start: string;
  end: string;
  duration?: string;
  seconds?: number;
  minutes?: number;
}

export interface TodayReport {
  // Schema versioning
  schema_version?: number;
  
  source_file?: string;
  date: string;
  title?: string;
  overview?: Overview;
  prepared_for_manager?: string[];
  executive_summary?: string[];
  accomplishments_today?: string[];
  
  // Schema v2 fields
  headline_bullets?: string[];
  proof?: {
    deep_work?: ProofEntry[];
    timeline?: ProofEntry[];
    apps?: ProofEntry[];
    meetings?: ProofEntry[];
  };
  raw?: Record<string, unknown>;
  
  // Legacy fields
  by_category?: Record<string, string>;
  browser_highlights?: unknown;
  timeline?: TimelineEntry[];
  deep_work?: DeepWorkEntry[];

  // Extended legacy fields used by the static dashboard
  hourly_focus?: HourlyFocusEntry[];
  deep_work_blocks?: DeepWorkBlock[];
  top_apps?: Record<string, string>;
  top_windows_preview?: string[];

  // Optional integration payloads (shape varies by source)
  google_workspace?: unknown;
  hubspot?: unknown;
  monday?: unknown;
  slack?: unknown;
  aloware?: unknown;

  // Optional narrative helpers
  client_summary?: unknown;
  next_up?: unknown;
  suggested_tasks?: unknown;
  notes?: unknown;
}

export interface ProofEntry {
  id: string;
  title: string;
  durationMinutes?: number;
  timeRange?: string;
  category?: string;
  label?: string;
}

export interface BulletItem {
  id: string;
  title: string;
  durationMinutes: number;
  category?: string;
  proof: ProofEntry[];
  hidden?: boolean;
  source?: string;
}
