import { useEffect, useMemo, useState } from 'react';
import { AlertCircle, Clipboard, ClipboardCheck, Merge, RefreshCw, Undo } from 'lucide-react';
import BulletCard from '../components/BulletCard';
import { candidateReportPaths, buildBulletItems } from '../lib/reportTransforms';
import type { BulletItem, TodayReport } from '../types/report';
import { formatMinutes } from '../utils/time';
import { clearPersistedBullets, loadPersistedBullets, persistBullets } from '../utils/storage';
import { todayLocalISO, yesterdayLocalISO } from '../utils/date';

async function fetchReport(date: string): Promise<TodayReport> {
  for (const path of candidateReportPaths(date)) {
    const response = await fetch(path);
    if (response.ok) {
      return response.json();
    }
  }
  throw new Error(`Report for ${date} not found`);
}

export default function TodayPage() {
  const [report, setReport] = useState<TodayReport | null>(null);
  const [reportDate, setReportDate] = useState<string>(todayLocalISO());
  const [bullets, setBullets] = useState<BulletItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mergeMode, setMergeMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [copied, setCopied] = useState(false);
  const [fallbackUsed, setFallbackUsed] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        let dateToUse = todayLocalISO();
        let data: TodayReport | null = null;
        try {
          data = await fetchReport(dateToUse);
          setFallbackUsed(false);
        } catch (err) {
          console.warn('Primary report missing, trying yesterday', err);
          dateToUse = yesterdayLocalISO();
          data = await fetchReport(dateToUse);
          setFallbackUsed(true);
        }

        if (cancelled || !data) return;
        const baselineBullets = buildBulletItems(data);
        const saved = loadPersistedBullets(dateToUse);

        setReport(data);
        setReportDate(data.date || dateToUse);
        setBullets(saved?.length ? saved : baselineBullets);
      } catch (err) {
        if (!cancelled) {
          console.error(err);
          setError('Unable to load the latest report. Try refreshing or regenerating reports.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (reportDate && bullets.length) {
      persistBullets(reportDate, bullets);
    }
  }, [reportDate, bullets]);

  const visibleBullets = useMemo(() => bullets.filter((b) => !b.hidden), [bullets]);
  const hiddenBullets = useMemo(() => bullets.filter((b) => b.hidden), [bullets]);

  const handleToggleSelect = (id: string) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const handleRename = (id: string, title: string) => {
    setBullets((prev) => prev.map((item) => (item.id === id ? { ...item, title } : item)));
  };

  const handleToggleHidden = (id: string) => {
    setBullets((prev) => prev.map((item) => (item.id === id ? { ...item, hidden: !item.hidden } : item)));
  };

  const handleMerge = () => {
    if (selectedIds.length < 2) return;
    const selected = bullets.filter((item) => selectedIds.includes(item.id));
    if (!selected.length) return;

    const totalMinutes = selected.reduce((sum, item) => sum + item.durationMinutes, 0);
    const categories = Array.from(new Set(selected.map((item) => item.category).filter(Boolean)));
    const defaultTitle = `${formatMinutes(totalMinutes)} ${categories.join(' + ') || 'Merged focus'}`;
    const userTitle = window.prompt('Name the merged summary bullet', defaultTitle) || defaultTitle;

    const merged: BulletItem = {
      id: `merged-${Date.now()}`,
      title: userTitle,
      durationMinutes: totalMinutes,
      category: categories.join(', ') || 'Merged',
      proof: selected.flatMap((item) => item.proof),
      source: 'merged',
    };

    const remaining = bullets.filter((item) => !selectedIds.includes(item.id));
    setBullets([...remaining, merged]);
    setSelectedIds([]);
    setMergeMode(false);
  };

  const handleCopy = async () => {
    const lines = visibleBullets.map((item) => `• ${item.title}`);
    try {
      await navigator.clipboard.writeText(lines.join('\n'));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Clipboard copy failed', err);
    }
  };

  const handleResetEdits = () => {
    if (!report) return;
    clearPersistedBullets(reportDate);
    setBullets(buildBulletItems(report));
    setMergeMode(false);
    setSelectedIds([]);
  };

  const summaryStats = useMemo(() => {
    if (!report?.overview) return [];
    const { active_time, focus_time, meetings_time, coverage_time } = report.overview;
    return [
      active_time && { label: 'Active', value: active_time },
      focus_time && { label: 'Focus', value: focus_time },
      meetings_time && { label: 'Meetings', value: meetings_time },
      coverage_time && { label: 'Coverage', value: coverage_time },
    ].filter(Boolean) as { label: string; value: string }[];
  }, [report]);

  if (loading) {
    return (
      <div className="glass-panel p-8 max-w-4xl mx-auto flex items-center gap-3 text-muted">
        <RefreshCw className="h-4 w-4 animate-spin" />
        Loading today&apos;s brief...
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-panel p-8 max-w-4xl mx-auto flex items-center gap-3 text-red-200">
        <AlertCircle className="h-5 w-5" />
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="glass-panel p-5 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-muted">{fallbackUsed ? 'Yesterday fallback' : 'Today'} report</p>
          <h2 className="text-2xl font-semibold text-white">{report?.title || `Daily Accomplishments — ${reportDate}`}</h2>
          <p className="text-sm text-muted">Data pulled from {reportDate}{fallbackUsed ? ' (today not found)' : ''}.</p>
          {report?.prepared_for_manager && (
            <p className="text-xs text-muted mt-1">Manager summary: {report.prepared_for_manager[0]}</p>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setMergeMode((prev) => !prev)}
            className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm border transition-colors ${
              mergeMode ? 'bg-accent/20 border-accent/60 text-white' : 'bg-white/5 border-white/10 text-muted hover:border-accent/50'
            }`}
          >
            <Merge className="h-4 w-4" />
            {mergeMode ? 'Select bullets to merge' : 'Merge bullets'}
          </button>
          <button
            type="button"
            onClick={handleMerge}
            disabled={!mergeMode || selectedIds.length < 2}
            className="inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm border border-white/10 bg-white/5 text-white disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ClipboardCheck className="h-4 w-4" />
            Merge selected
          </button>
          <button
            type="button"
            onClick={handleCopy}
            className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm border ${
              copied ? 'bg-emerald-500/20 border-emerald-400/60 text-white' : 'bg-white/5 border-white/10 text-white hover:border-accent/60'
            }`}
          >
            {copied ? <ClipboardCheck className="h-4 w-4" /> : <Clipboard className="h-4 w-4" />}
            {copied ? 'Copied!' : 'Copy Slack bullets'}
          </button>
          <button
            type="button"
            onClick={handleResetEdits}
            className="inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm border border-white/10 text-muted hover:text-white hover:border-accent/60"
          >
            <Undo className="h-4 w-4" />
            Reset edits
          </button>
        </div>
      </div>

      {summaryStats.length > 0 && (
        <div className="glass-panel p-4 flex flex-wrap gap-3 text-sm text-muted">
          {summaryStats.map((item) => (
            <div
              key={item.label}
              className="flex items-center gap-2 rounded-full bg-white/5 px-3 py-1 border border-white/10"
            >
              <span className="uppercase text-[10px] tracking-[0.2em] text-accent">{item.label}</span>
              <span className="text-white font-semibold">{item.value}</span>
            </div>
          ))}
        </div>
      )}

      <div className="space-y-4">
        <p className="text-xs uppercase tracking-[0.25em] text-muted">Headline bullets</p>
        {visibleBullets.length === 0 && (
          <div className="glass-panel p-6 text-muted flex items-center gap-2">
            <AlertCircle className="h-4 w-4" />
            No bullets available. Try resetting edits or regenerating reports.
          </div>
        )}
        <div className="space-y-4">
          {visibleBullets.map((item) => (
            <BulletCard
              key={item.id}
              item={item}
              mergeMode={mergeMode}
              selected={selectedIds.includes(item.id)}
              onToggleSelect={handleToggleSelect}
              onToggleHidden={handleToggleHidden}
              onRename={handleRename}
            />
          ))}
        </div>
      </div>

      {hiddenBullets.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-xs uppercase tracking-[0.25em] text-muted">
            <AlertCircle className="h-4 w-4" /> Hidden bullets
          </div>
          <div className="space-y-2">
            {hiddenBullets.map((item) => (
              <BulletCard
                key={item.id}
                item={item}
                mergeMode={false}
                selected={false}
                onToggleHidden={handleToggleHidden}
                onRename={handleRename}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
