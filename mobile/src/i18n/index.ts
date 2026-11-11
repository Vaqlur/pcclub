import { ApiError } from '@/api/client';
import { parseDateKey, toZoned, weekday, dateKey } from '@/lib/time';

import { ru } from './ru';

/** The app is Russian-only for now; this is the one place to switch languages later. */
export const t = ru;

/** A message for any thrown value, localized by the API's error code. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return t.errors[error.code] ?? t.errors.UNKNOWN;
  return t.errors.UNKNOWN;
}

/** `10:00–23:00`, or "round the clock" when the club never closes. */
export function openingHoursLabel(club: { opens_at: string | null; closes_at: string | null }): string {
  if (club.opens_at === null || club.closes_at === null) return t.common.roundTheClock;
  return `${club.opens_at.slice(0, 5)}–${club.closes_at.slice(0, 5)}`;
}

const NARROW_SPACE = ' ';

/** Whole tenge, e.g. `1 500 ₸`. */
export function formatKzt(amount: number): string {
  return `${String(amount).replace(/\B(?=(\d{3})+(?!\d))/g, NARROW_SPACE)} ₸`;
}

/** `пн, 1 июн` for a `YYYY-MM-DD` calendar date. */
export function formatDay(key: string): string {
  const { month, day } = parseDateKey(key);
  return `${t.weekdays[weekday(key)]}, ${day} ${t.months[month - 1]}`;
}

/** `пн, 1 июн` for an instant, on the club's calendar. */
export function formatInstantDay(ms: number, timeZone: string): string {
  return formatDay(dateKey(toZoned(ms, timeZone)));
}

export function formatDuration(minutes: number): string {
  return t.hours(Math.floor(minutes / 60), minutes % 60);
}

/** `M:SS` countdown. */
export function formatCountdown(ms: number): string {
  const seconds = Math.max(0, Math.ceil(ms / 1000));
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
}
