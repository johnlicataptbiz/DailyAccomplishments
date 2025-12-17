import type { ProofEntry } from '../types/report';
import { formatMinutes } from '../utils/time';

interface Props {
  entries: ProofEntry[];
}

export default function ProofList({ entries }: Props) {
  if (!entries.length) {
    return <p className="text-sm text-muted">No detailed proof captured for this item.</p>;
  }

  return (
    <ul className="space-y-2">
      {entries.map((entry) => (
        <li
          key={entry.id}
          className="flex items-start gap-3 rounded-lg bg-slate-50 px-3 py-2 border border-slate-200 text-sm"
        >
          <div className="mt-0.5 h-2 w-2 rounded-full bg-accent" />
          <div className="flex flex-col gap-1">
            <div className="flex flex-wrap items-center gap-2 text-slate-900">
              <span className="font-medium">{entry.title}</span>
              {entry.timeRange && <span className="text-xs text-muted">{entry.timeRange}</span>}
            </div>
            <div className="flex gap-3 text-xs text-muted">
              {entry.durationMinutes !== undefined && (
                <span className="inline-flex items-center gap-1 rounded-full bg-panel border border-slate-200 px-2 py-0.5">
                  {formatMinutes(entry.durationMinutes)}
                </span>
              )}
              {entry.category && (
                <span className="inline-flex items-center gap-1 rounded-full bg-panel border border-slate-200 px-2 py-0.5">
                  {entry.category}
                </span>
              )}
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
}
