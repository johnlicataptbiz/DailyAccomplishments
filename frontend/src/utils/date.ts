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

export function addDaysISO(dateISO: string, deltaDays: number): string {
  const [year, month, day] = dateISO.split('-').map((v) => Number(v));
  const d = new Date(year, (month || 1) - 1, day || 1);
  d.setDate(d.getDate() + deltaDays);
  return formatDateISO(d);
}
