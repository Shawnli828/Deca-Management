export const DATE_PRESETS = [
  { key: 'today', label: 'Today' },
  { key: 'yesterday', label: 'Yesterday' },
  { key: '7d', label: 'Last 7 days' },
  { key: '30d', label: 'Last 30 days' },
  { key: '3m', label: 'Last 3 months' },
  { key: '6m', label: 'Last 6 months' }
] as const;

export type DatePresetKey = typeof DATE_PRESETS[number]['key'];

export function dateInputValue(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

export function parseInputDate(value: string) {
  const [year, month, day] = value.split('-').map(Number);
  return new Date(year, (month || 1) - 1, day || 1);
}

export function addDays(date: Date, days: number) {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

export function addMonths(date: Date, months: number) {
  const next = new Date(date);
  next.setMonth(next.getMonth() + months);
  return next;
}

export function rangeForPreset(preset: DatePresetKey) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  if (preset === 'today') return { from: dateInputValue(today), to: dateInputValue(today) };
  const yesterday = addDays(today, -1);
  if (preset === 'yesterday') {
    return { from: dateInputValue(yesterday), to: dateInputValue(yesterday) };
  }
  if (preset === '30d') return { from: dateInputValue(addDays(today, -30)), to: dateInputValue(yesterday) };
  if (preset === '3m') return { from: dateInputValue(addMonths(today, -3)), to: dateInputValue(yesterday) };
  if (preset === '6m') return { from: dateInputValue(addMonths(today, -6)), to: dateInputValue(yesterday) };
  return { from: dateInputValue(addDays(today, -7)), to: dateInputValue(yesterday) };
}

export function displayDateRange(from: string, to: string) {
  const formatter = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  return `${formatter.format(parseInputDate(from))} - ${formatter.format(parseInputDate(to))}`;
}

export function sameDate(left: string, right: string) {
  return left === right;
}

export const defaultDateRange = rangeForPreset('7d');
