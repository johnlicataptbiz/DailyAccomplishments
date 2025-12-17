import type { BulletItem } from '../types/report';

const SCHEMA_VERSION = 1;

interface PersistedState {
  version: number;
  updatedAt: string;
  bullets: BulletItem[];
}

function storageKey(date: string) {
  return `today-brief-${date}`;
}

export function loadPersistedBullets(date: string): BulletItem[] | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem(storageKey(date));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as PersistedState;
    if (parsed.version !== SCHEMA_VERSION || !Array.isArray(parsed.bullets)) return null;
    return parsed.bullets;
  } catch (error) {
    console.error('Failed to load persisted bullets', error);
    return null;
  }
}

export function persistBullets(date: string, bullets: BulletItem[]) {
  if (typeof window === 'undefined') return;
  try {
    const payload: PersistedState = {
      version: SCHEMA_VERSION,
      updatedAt: new Date().toISOString(),
      bullets,
    };
    localStorage.setItem(storageKey(date), JSON.stringify(payload));
  } catch (error) {
    console.error('Failed to persist bullets', error);
  }
}

export function clearPersistedBullets(date: string) {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(storageKey(date));
}
