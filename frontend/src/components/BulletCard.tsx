import { useMemo, useState } from 'react';
import { CheckSquare, ChevronDown, ChevronRight, Eye, EyeOff, Pencil, Save, X } from 'lucide-react';
import type { BulletItem } from '../types/report';
import { formatMinutes } from '../utils/time';
import ProofList from './ProofList';

interface Props {
  item: BulletItem;
  mergeMode?: boolean;
  selected?: boolean;
  onToggleSelect?: (id: string) => void;
  onToggleHidden: (id: string) => void;
  onRename: (id: string, title: string) => void;
}

export default function BulletCard({
  item,
  mergeMode,
  selected,
  onToggleSelect,
  onToggleHidden,
  onRename,
}: Props) {
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(item.title);

  const categoryTone = useMemo(() => {
    if (item.category?.toLowerCase().includes('meeting')) return 'bg-orange-50 text-orange-800 border-orange-200';
    if (item.category?.toLowerCase().includes('coding')) return 'bg-emerald-50 text-emerald-800 border-emerald-200';
    if (item.category?.toLowerCase().includes('research')) return 'bg-sky-50 text-sky-800 border-sky-200';
    return 'bg-slate-50 text-slate-800 border-slate-200';
  }, [item.category]);

  const headerActions = (
    <div className="flex items-center gap-2">
      {mergeMode && (
        <button
          type="button"
          onClick={() => onToggleSelect?.(item.id)}
          className={`flex items-center gap-2 rounded-full px-3 py-1 text-xs border transition-colors ${
            selected
              ? 'bg-soft border-accent/40 text-slate-900'
              : 'bg-panel border-slate-200 text-slate-600 hover:border-accent/40'
          }`}
        >
          <CheckSquare className="h-4 w-4" />
          {selected ? 'Selected' : 'Select'}
        </button>
      )}
      {!mergeMode && (
        <button
          type="button"
          onClick={() => setEditing(true)}
          className="rounded-full p-2 text-slate-500 hover:text-slate-900 hover:bg-slate-50"
          aria-label="Edit bullet"
        >
          <Pencil className="h-4 w-4" />
        </button>
      )}
      {!mergeMode && (
        <button
          type="button"
          onClick={() => onToggleHidden(item.id)}
          className="rounded-full p-2 text-slate-500 hover:text-slate-900 hover:bg-slate-50"
          aria-label={item.hidden ? 'Show item' : 'Hide item'}
        >
          {item.hidden ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
        </button>
      )}
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="rounded-full p-2 text-slate-500 hover:text-slate-900 hover:bg-slate-50"
        aria-label="Toggle proof"
      >
        {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
      </button>
    </div>
  );

  return (
    <div
      className={`glass-panel p-5 space-y-3 ${item.hidden ? 'opacity-60 border-dashed' : ''}`}
    >
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="flex items-start gap-3">
          <div className="mt-1 h-2.5 w-2.5 rounded-full bg-accent" />
          <div className="space-y-2">
            {editing ? (
              <div className="flex flex-col gap-2 md:flex-row md:items-center">
                <input
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  className="w-full rounded-lg bg-panel px-3 py-2 text-sm border border-slate-200 text-slate-900"
                />
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      onRename(item.id, draft.trim() || item.title);
                      setEditing(false);
                    }}
                    className="inline-flex items-center gap-2 rounded-full bg-soft px-3 py-2 text-xs text-slate-900 border border-accent/40"
                  >
                    <Save className="h-4 w-4" /> Save
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setEditing(false);
                      setDraft(item.title);
                    }}
                    className="inline-flex items-center gap-2 rounded-full px-3 py-2 text-xs text-slate-600 border border-slate-200 hover:bg-slate-50"
                  >
                    <X className="h-4 w-4" /> Cancel
                  </button>
                </div>
              </div>
            ) : (
              <>
                <p className="text-lg font-semibold text-slate-900">{item.title}</p>
                <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                  <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1 border ${categoryTone}`}>
                    {item.category || 'Summary'}
                  </span>
                  <span className="inline-flex items-center gap-2 rounded-full px-3 py-1 bg-panel border border-slate-200 text-slate-900">
                    {formatMinutes(item.durationMinutes)}
                  </span>
                  {item.source && <span className="uppercase tracking-wide text-[10px] text-muted">{item.source}</span>}
                </div>
              </>
            )}
          </div>
        </div>
        {headerActions}
      </div>

      {open && (
        <div className="pt-2">
          <p className="text-xs uppercase tracking-[0.2em] text-muted mb-3">Proof</p>
          <ProofList entries={item.proof} />
        </div>
      )}
    </div>
  );
}
