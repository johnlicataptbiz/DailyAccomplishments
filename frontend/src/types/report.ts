export interface Overview {
  active_time?: string;
  focus_time?: string;
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
  category?: string;
  label?: string;
  app?: string;
  details?: string;
}

export interface TodayReport {
  source_file?: string;
  date: string;
  title?: string;
  overview?: Overview;
  prepared_for_manager?: string[];
  executive_summary?: string[];
  accomplishments_today?: string[];
  by_category?: Record<string, string>;
  browser_highlights?: unknown;
  timeline?: TimelineEntry[];
  deep_work?: DeepWorkEntry[];
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
