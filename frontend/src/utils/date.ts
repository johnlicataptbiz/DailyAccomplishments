export function formatDateISO(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export function todayLocalISO(): string {
  return formatDateISO(new Date());
}

export function yesterdayLocalISO(): string {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return formatDateISO(d);
}
