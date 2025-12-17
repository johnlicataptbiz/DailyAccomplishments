import { useEffect, useMemo, useState } from 'react';
import {
  AlertCircle,
  Calendar,
  CalendarDays,
  Settings,
  Shield,
  ShieldOff,
} from 'lucide-react';
import { addDaysISO, todayLocalISO } from '../utils/date';
import { formatMinutes, parseDurationToMinutes } from '../utils/time';
import { candidateReportPaths } from '../lib/reportTransforms';
import type { TodayReport } from '../types/report';

type RangeMode = 'day' | '7d';

interface Baseline {
  days: number;
  focusAvg: number;
  meetingAvg: number;
  activeAvg: number;
  interruptsAvg: number;
}

async function fetchReport(date: string): Promise<TodayReport> {
  for (const path of candidateReportPaths(date)) {
    const response = await fetch(path);
    if (response.ok) {
      return response.json();
    }
  }
  throw new Error(`Report for ${date} not found`);
}

function formatDateFriendly(dateISO: string): string {
  const [y, m, d] = dateISO.split('-').map((v) => Number(v));
  const date = new Date(y, (m || 1) - 1, d || 1);
  return date.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: '2-digit', year: 'numeric' });
}

function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n));
}

function safeRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function computeInterrupts(report: TodayReport): number {
  const timeline = report.timeline ?? [];
  let lastApp: string | undefined;
  let switches = 0;

  for (const entry of timeline) {
    const seconds = entry.seconds;
    const minutes = entry.minutes ?? 0;
    const isActive = (typeof seconds === 'number' && seconds > 0) || minutes > 0;
    if (!isActive) continue;

    const app = entry.app?.trim();
    if (!app) continue;
    if (lastApp && app !== lastApp) switches += 1;
    lastApp = app;
  }

  return switches;
}

function computeProductivityScore(focusMinutes: number, meetingMinutes: number, activeMinutes: number, interrupts: number) {
  if (!activeMinutes) return { score: 0, label: '—' };
  const focusRatio = clamp(focusMinutes / activeMinutes, 0, 1);
  const meetingRatio = clamp(meetingMinutes / activeMinutes, 0, 1);

  const base = focusRatio * 100;
  const meetingPenalty = meetingRatio * 18;
  const interruptPenalty = Math.min(18, interrupts * 0.6);
  const score = clamp(Math.round(base - meetingPenalty - interruptPenalty + 10), 0, 100);

  const label =
    score >= 85 ? 'Excellent' :
    score >= 70 ? 'Good' :
    score >= 55 ? 'Typical' :
    score >= 40 ? 'Low' :
    'Needs focus';

  return { score, label };
}

function deltaBadge(today: number, avg: number, invert = false) {
  if (!avg) return null;
  const change = Math.round(((today - avg) / Math.max(1, avg)) * 100);
  const upGood = invert ? change < 0 : change > 0;
  const color = upGood ? 'text-emerald-600' : 'text-orange-600';
  const arrow = change === 0 ? '•' : change > 0 ? '▲' : '▼';
  return { text: `${arrow} ${Math.abs(change)}% vs 7d avg`, color };
}

function Donut({
  segments,
}: {
  segments: { label: string; minutes: number; color: string }[];
}) {
  const total = segments.reduce((sum, s) => sum + s.minutes, 0);
  const normalized = segments
    .filter((s) => s.minutes > 0)
    .map((s) => ({ ...s, pct: total ? (s.minutes / total) * 100 : 0 }));

  const gradientStops = normalized.reduce<{ stops: string[]; cum: number }>(
    (state, s) => {
      const start = state.cum;
      const end = start + s.pct;
      return {
        stops: [...state.stops, `${s.color} ${start.toFixed(2)}% ${end.toFixed(2)}%`],
        cum: end,
      };
    },
    { stops: [], cum: 0 },
  ).stops;

  const background = gradientStops.length
    ? `conic-gradient(${gradientStops.join(', ')})`
    : 'conic-gradient(#e2e8f0 0% 100%)';

  return (
    <div className="flex flex-col md:flex-row gap-6 items-start">
      <div
        className="h-44 w-44 rounded-full relative shrink-0"
        style={{ background }}
        aria-label="Category distribution donut chart"
      >
        <div className="absolute inset-6 rounded-full bg-panel border border-slate-200" />
      </div>
      <div className="space-y-2 w-full">
        {normalized.length ? (
          normalized.map((s) => (
            <div key={s.label} className="flex items-center justify-between gap-3 text-sm">
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: s.color }} />
                <span className="text-slate-700">{s.label}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-slate-500">{formatMinutes(s.minutes)}</span>
                <span className="text-slate-400 tabular-nums w-14 text-right">{Math.round(s.pct)}%</span>
              </div>
            </div>
          ))
        ) : (
          <p className="text-sm text-muted">No category data found for this day.</p>
        )}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [dateISO, setDateISO] = useState(() => todayLocalISO());
  const [rangeMode, setRangeMode] = useState<RangeMode>('day');
  const [report, setReport] = useState<TodayReport | null>(null);
  const [baseline, setBaseline] = useState<Baseline | null>(null);
  const [privacyMode, setPrivacyMode] = useState<boolean>(() => {
    if (typeof window === 'undefined') return true;
    const raw = localStorage.getItem('da-privacy-mode');
    return raw ? raw === 'true' : true;
  });
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('da-privacy-mode', String(privacyMode));
    }
  }, [privacyMode]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchReport(dateISO);
        if (cancelled) return;
        setReport(data);

        // Background-load baseline for deltas.
        const dailyMetrics: { focus: number; meeting: number; active: number; interrupts: number }[] = [];
        for (let i = 1; i <= 7; i += 1) {
          const d = addDaysISO(dateISO, -i);
          try {
            const r = await fetchReport(d);
            const focus = parseDurationToMinutes(r.overview?.focus_time);
            const meeting = parseDurationToMinutes(r.overview?.meetings_time);
            const active = parseDurationToMinutes(r.overview?.active_time);
            dailyMetrics.push({ focus, meeting, active, interrupts: computeInterrupts(r) });
          } catch {
            // Missing reports are expected; just skip them.
          }
        }
        if (cancelled) return;
        if (dailyMetrics.length) {
          const sum = dailyMetrics.reduce(
            (acc, cur) => ({
              focus: acc.focus + cur.focus,
              meeting: acc.meeting + cur.meeting,
              active: acc.active + cur.active,
              interrupts: acc.interrupts + cur.interrupts,
            }),
            { focus: 0, meeting: 0, active: 0, interrupts: 0 },
          );
          setBaseline({
            days: dailyMetrics.length,
            focusAvg: sum.focus / dailyMetrics.length,
            meetingAvg: sum.meeting / dailyMetrics.length,
            activeAvg: sum.active / dailyMetrics.length,
            interruptsAvg: sum.interrupts / dailyMetrics.length,
          });
        } else {
          setBaseline(null);
        }
      } catch (err) {
        console.error(err);
        if (!cancelled) setError('Unable to load the selected report. Pick another date or regenerate reports.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [dateISO]);

  const metrics = useMemo(() => {
    const focusMinutes = parseDurationToMinutes(report?.overview?.focus_time);
    const meetingMinutes = parseDurationToMinutes(report?.overview?.meetings_time);
    const activeMinutes = parseDurationToMinutes(report?.overview?.active_time);
    const interrupts = report ? computeInterrupts(report) : 0;
    const productivity = computeProductivityScore(focusMinutes, meetingMinutes, activeMinutes, interrupts);
    return { focusMinutes, meetingMinutes, activeMinutes, interrupts, productivity };
  }, [report]);

  const categorySegments = useMemo(() => {
    const categories = report?.by_category ?? {};
    const palette = ['#1d4ed8', '#10b981', '#f97316', '#8b5cf6', '#eab308', '#ec4899', '#64748b'];
    const entries = Object.entries(categories)
      .map(([label, value]) => ({ label, minutes: parseDurationToMinutes(value) }))
      .filter((e) => e.minutes > 0)
      .sort((a, b) => b.minutes - a.minutes);
    return entries.map((e, idx) => ({ ...e, color: palette[idx % palette.length] }));
  }, [report]);

  const topApps = useMemo(() => {
    const raw = report?.top_apps ?? {};
    const entries = Object.entries(raw)
      .map(([name, value]) => ({ name, minutes: parseDurationToMinutes(value) }))
      .filter((e) => e.minutes > 0)
      .sort((a, b) => b.minutes - a.minutes)
      .slice(0, 8);
    const max = entries[0]?.minutes ?? 1;
    const maskedNames = new Map<string, string>();
    entries.forEach((e, idx) => maskedNames.set(e.name, `App ${idx + 1}`));
    return entries.map((e) => ({
      ...e,
      label: privacyMode ? maskedNames.get(e.name) ?? 'App' : e.name,
      pct: Math.round((e.minutes / max) * 100),
    }));
  }, [report, privacyMode]);

  const hourly = useMemo(() => {
    const hours = report?.hourly_focus ?? [];
    const cleaned = hours
      .filter((h) => h && typeof h.hour === 'number')
      .map((h) => ({ hour: h.hour, minutes: parseDurationToMinutes(h.time) }))
      .filter((h) => h.hour >= 6 && h.hour <= 20);
    const max = cleaned.reduce((m, h) => Math.max(m, h.minutes), 1);
    return { hours: cleaned, max };
  }, [report]);

  const deepWorkBlocks = useMemo(() => {
    const blocks = report?.deep_work_blocks ?? [];
    return blocks
      .map((b) => ({
        start: b.start,
        end: b.end,
        minutes: b.minutes ?? (b.seconds ? Math.round(b.seconds / 60) : 0),
      }))
      .filter((b) => b.minutes > 0)
      .slice(0, 8);
  }, [report]);

  const integrations = useMemo(() => {
    const out: { name: string; value: string; detail?: string }[] = [];
    const monday = safeRecord(report?.monday);
    if (monday) {
      const itemsUpdated = Number(monday.items_updated ?? 0);
      const boards = safeRecord(monday.by_board);
      const boardCount = boards ? Object.keys(boards).length : 0;
      if (itemsUpdated || boardCount) {
        out.push({ name: 'Monday', value: `${itemsUpdated} tasks`, detail: `${boardCount} boards` });
      }
    }

    const hubspot = safeRecord(report?.hubspot);
    if (hubspot) {
      const calls = Array.isArray(hubspot.calls) ? hubspot.calls.length : 0;
      const emails = Array.isArray(hubspot.emails) ? hubspot.emails.length : 0;
      const deals = Array.isArray(hubspot.deals) ? hubspot.deals.length : 0;
      if (calls || emails || deals) {
        out.push({ name: 'HubSpot', value: `${deals} deals`, detail: `${calls} calls • ${emails} emails` });
      }
    }

    const gws = safeRecord(report?.google_workspace);
    if (gws) {
      const gCal = String((gws['Google Calendar'] as string | undefined) ?? '');
      const gmail = String((gws.Gmail as string | undefined) ?? '');
      const sheets = String((gws['Google Sheets'] as string | undefined) ?? '');
      const any = [gCal, gmail, sheets].some((v) => v && v !== '00:00');
      if (any) {
        out.push({ name: 'Google', value: 'Workspace', detail: [sheets && `Sheets ${sheets}`, gCal && `Cal ${gCal}`].filter(Boolean).join(' • ') });
      }
    }

    const meetingStr = report?.overview?.meetings_time;
    const meetingMinutes = parseDurationToMinutes(meetingStr);
    if (meetingMinutes > 0) {
      out.push({ name: 'Calendar', value: formatMinutes(meetingMinutes), detail: 'Meetings' });
    }

    const slack = safeRecord(report?.slack);
    if (slack) {
      const stats = safeRecord(slack.stats);
      const sent = Number(stats?.total_sent ?? 0);
      const received = Number(stats?.total_received ?? 0);
      if (sent || received) out.push({ name: 'Slack', value: `${sent} sent`, detail: `${received} received` });
    }

    const aloware = safeRecord(report?.aloware);
    if (aloware) {
      const calls = Number(aloware.total_calls ?? 0);
      const talk = String(aloware.talk_time ?? '');
      if (calls || talk) out.push({ name: 'Aloware', value: `${calls} calls`, detail: talk ? `${talk} talk` : undefined });
    }

    return out.slice(0, 6);
  }, [report]);

  const narrative = useMemo(() => {
    const title = report?.title || `Daily Summary — ${dateISO}`;
    const summary =
      report?.executive_summary?.[0] ||
      report?.prepared_for_manager?.[0] ||
      report?.accomplishments_today?.[0] ||
      'No narrative summary available for this day yet.';
    return { title, summary };
  }, [report, dateISO]);

  if (loading) {
    return (
      <div className="glass-panel p-8 max-w-6xl mx-auto flex items-center gap-3 text-muted">
        Loading dashboard…
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-panel p-8 max-w-6xl mx-auto flex items-center gap-3 text-red-700 bg-red-50 border-red-200">
        <AlertCircle className="h-5 w-5" />
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="glass-panel p-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setDateISO(todayLocalISO())}
            className="inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm bg-panel border border-slate-200 hover:border-accent/40"
          >
            <Calendar className="h-4 w-4 text-accent" />
            Today
          </button>
          <label className="inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm bg-panel border border-slate-200 hover:border-accent/40 cursor-pointer">
            <CalendarDays className="h-4 w-4 text-accent" />
            <span className="text-slate-700">{formatDateFriendly(dateISO)}</span>
            <input
              type="date"
              value={dateISO}
              onChange={(e) => setDateISO(e.target.value)}
              className="sr-only"
            />
          </label>
          <button
            type="button"
            onClick={() => setRangeMode((prev) => (prev === 'day' ? '7d' : 'day'))}
            className={`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm border ${
              rangeMode === '7d'
                ? 'bg-soft border-accent/40 text-slate-900'
                : 'bg-panel border-slate-200 text-slate-700 hover:border-accent/40'
            }`}
          >
            Last 7 Days
          </button>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setPrivacyMode((p) => !p)}
            className="inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm bg-panel border border-slate-200 hover:border-accent/40"
            aria-pressed={privacyMode}
          >
            {privacyMode ? <Shield className="h-4 w-4 text-accent" /> : <ShieldOff className="h-4 w-4 text-slate-500" />}
            <span className="text-slate-700">Privacy Mode: {privacyMode ? 'ON' : 'OFF'}</span>
          </button>
          <button
            type="button"
            onClick={() => setSettingsOpen(true)}
            className="inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm bg-panel border border-slate-200 hover:border-accent/40"
          >
            <Settings className="h-4 w-4 text-slate-600" />
            Settings
          </button>
        </div>
      </div>

      <section className="glass-panel p-6 bg-gradient-to-br from-white to-sky-50">
        <p className="text-xs uppercase tracking-[0.16em] text-slate-500">The Daily Narrative</p>
        <h2 className="text-2xl md:text-3xl font-semibold text-slate-900 mt-2">{narrative.title}</h2>
        <p className="text-sm md:text-base text-slate-600 mt-3 max-w-3xl">{narrative.summary}</p>
      </section>

      <section className="glass-panel p-6">
        <p className="text-xs uppercase tracking-[0.16em] text-slate-500 mb-4">Key Productivity Metrics</p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="rounded-2xl border border-slate-200 bg-soft p-4">
            <p className="text-xs text-slate-500">Productivity Score</p>
            <div className="mt-2 flex items-end gap-2">
              <p className="text-3xl font-semibold text-slate-900 tabular-nums">{metrics.productivity.score}</p>
              <p className="text-sm text-slate-500">/100</p>
            </div>
            <p className="text-xs text-slate-500 mt-1">({metrics.productivity.label})</p>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-soft p-4">
            <p className="text-xs text-slate-500">Focus Time</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900 tabular-nums">{formatMinutes(metrics.focusMinutes)}</p>
            {baseline?.days ? (
              <p className={`text-xs mt-1 ${deltaBadge(metrics.focusMinutes, baseline.focusAvg)?.color ?? 'text-slate-500'}`}>
                {deltaBadge(metrics.focusMinutes, baseline.focusAvg)?.text}
              </p>
            ) : (
              <p className="text-xs text-slate-500 mt-1">No 7-day baseline yet</p>
            )}
          </div>

          <div className="rounded-2xl border border-slate-200 bg-soft p-4">
            <p className="text-xs text-slate-500">Meeting Time</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900 tabular-nums">{formatMinutes(metrics.meetingMinutes)}</p>
            {baseline?.days ? (
              <p className={`text-xs mt-1 ${deltaBadge(metrics.meetingMinutes, baseline.meetingAvg, true)?.color ?? 'text-slate-500'}`}>
                {deltaBadge(metrics.meetingMinutes, baseline.meetingAvg, true)?.text}
              </p>
            ) : (
              <p className="text-xs text-slate-500 mt-1">No 7-day baseline yet</p>
            )}
          </div>

          <div className="rounded-2xl border border-slate-200 bg-soft p-4">
            <p className="text-xs text-slate-500">Interrupts</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900 tabular-nums">{metrics.interrupts}</p>
            {baseline?.days ? (
              <p className="text-xs text-slate-500 mt-1">
                Avg {Math.round(baseline.interruptsAvg)} (7d)
              </p>
            ) : (
              <p className="text-xs text-slate-500 mt-1">Context switches</p>
            )}
          </div>
        </div>

        <p className="text-xs text-slate-500 mt-4">
          Total Active Time: {formatMinutes(metrics.activeMinutes)}
          {report?.overview?.coverage_window ? ` | Coverage: ${report.overview.coverage_window}` : ''}
        </p>
      </section>

      <section className="glass-panel p-6">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Activity Timeline & Deep Work Overlay</p>
            <p className="text-sm text-slate-600 mt-1">Hourly focus intensity (6:00–20:00)</p>
          </div>
          {rangeMode === '7d' && baseline?.days ? (
            <span className="text-xs text-slate-500">Showing day view; deltas computed from last {baseline.days} days</span>
          ) : null}
        </div>

        <div className="mt-4 flex items-end gap-2 overflow-x-auto pb-2">
          {hourly.hours.map((h) => (
            <div key={h.hour} className="flex flex-col items-center gap-2 w-10 shrink-0">
              <div className="h-24 w-6 rounded-full bg-slate-100 border border-slate-200 relative overflow-hidden">
                <div
                  className="absolute bottom-0 left-0 right-0 bg-accent/70"
                  style={{ height: `${Math.round((h.minutes / hourly.max) * 100)}%` }}
                />
              </div>
              <span className="text-[10px] text-slate-500">{String(h.hour).padStart(2, '0')}</span>
            </div>
          ))}
        </div>

        {deepWorkBlocks.length ? (
          <div className="mt-4 flex flex-wrap gap-2">
            {deepWorkBlocks.map((b) => (
              <span
                key={`${b.start}-${b.end}-${b.minutes}`}
                className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-700"
              >
                <span className="h-2 w-2 rounded-full bg-accent" />
                Deep work {b.start}–{b.end} ({b.minutes}m)
              </span>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted mt-4">No deep work blocks recorded for this day.</p>
        )}
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-panel p-6">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500 mb-4">Category Distribution</p>
          <Donut segments={categorySegments} />
        </div>

        <div className="glass-panel p-6">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500 mb-4">Top Applications</p>
          {topApps.length ? (
            <div className="space-y-3">
              {topApps.map((app, idx) => (
                <div key={app.label} className="flex items-center gap-3">
                  <div className="w-6 text-xs text-slate-400 tabular-nums">{idx + 1}.</div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm text-slate-800">{app.label}</p>
                      <p className="text-xs text-slate-500 tabular-nums">{formatMinutes(app.minutes)}</p>
                    </div>
                    <div className="mt-1 h-2 rounded-full bg-slate-100 border border-slate-200 overflow-hidden">
                      <div className="h-full bg-accent/70" style={{ width: `${app.pct}%` }} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted">No application breakdown found for this day.</p>
          )}
        </div>
      </section>

      <section className="glass-panel p-6">
        <p className="text-xs uppercase tracking-[0.16em] text-slate-500 mb-4">Integration Highlights</p>
        {integrations.length ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {integrations.map((card) => (
              <div key={card.name} className="rounded-2xl border border-slate-200 bg-soft p-4">
                <p className="text-xs text-slate-500">{card.name}</p>
                <p className="mt-2 text-lg font-semibold text-slate-900">{card.value}</p>
                {card.detail ? <p className="text-xs text-slate-500 mt-1">{card.detail}</p> : null}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted">No integration payloads present for this day.</p>
        )}
      </section>

      {settingsOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <button
            type="button"
            className="absolute inset-0 bg-slate-900/40"
            onClick={() => setSettingsOpen(false)}
            aria-label="Close settings"
          />
          <div className="relative w-full max-w-lg glass-panel p-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="text-lg font-semibold text-slate-900">Settings</h3>
                <p className="text-sm text-muted mt-1">Local-only preferences for this dashboard.</p>
              </div>
              <button
                type="button"
                onClick={() => setSettingsOpen(false)}
                className="rounded-xl px-3 py-2 text-sm border border-slate-200 bg-panel hover:border-accent/40"
              >
                Close
              </button>
            </div>

            <div className="mt-6 space-y-4">
              <label className="flex items-center justify-between gap-4">
                <span className="text-sm text-slate-700">Privacy mode (hide app names)</span>
                <input
                  type="checkbox"
                  checked={privacyMode}
                  onChange={(e) => setPrivacyMode(e.target.checked)}
                  className="h-4 w-4 accent-accent"
                />
              </label>
              <div className="text-xs text-slate-500">
                Productivity score is a heuristic based on focus/meetings/context switches; tune it later in the generator if you want a canonical score.
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
