/**
 * Slot grid for the booking screen. These mirror the server's rules only to draw a sensible
 * picker; the server validates every booking and its answer is final.
 * Pure functions: the current time is always passed in.
 */

import { fromZoned, parseDateKey, parseTimeOfDay } from './time.ts';

export const SLOT_MINUTES = 30;
export const MIN_BOOKING_MINUTES = 60;
export const MAX_BOOKING_MINUTES = 12 * 60;
export const MAX_ADVANCE_DAYS = 14;

const MINUTE_MS = 60_000;
const DAY_MINUTES = 24 * 60;

export type Interval = { start: number; end: number };

/** Opening hours as minutes since midnight; `null` means open around the clock. */
export type OpeningHours = { opens: number; closes: number } | null;

export function openingHours(opensAt: string | null, closesAt: string | null): OpeningHours {
  if (opensAt === null || closesAt === null) return null;
  return { opens: parseTimeOfDay(opensAt), closes: parseTimeOfDay(closesAt) };
}

/** Whether the shortest booking starting at `minuteOfDay` fits inside the opening hours. */
function canStartAt(minuteOfDay: number, hours: OpeningHours): boolean {
  if (hours === null) return true;
  const end = minuteOfDay + MIN_BOOKING_MINUTES;
  if (hours.opens < hours.closes) return minuteOfDay >= hours.opens && end <= hours.closes;
  // Overnight club (e.g. 18:00-04:00): open from `opens` to midnight and from midnight to `closes`.
  return minuteOfDay >= hours.opens || end <= hours.closes;
}

/** Instants of every possible booking start on a club-local day, aligned to the slot size. */
export function daySlotStarts(day: string, timeZone: string, hours: OpeningHours): number[] {
  const date = parseDateKey(day);
  const starts: number[] = [];
  for (let minute = 0; minute < DAY_MINUTES; minute += SLOT_MINUTES) {
    if (!canStartAt(minute, hours)) continue;
    starts.push(fromZoned({ ...date, hour: Math.floor(minute / 60), minute: minute % 60 }, timeZone));
  }
  return starts;
}

export function slotEnd(start: number, minutes: number): number {
  return start + minutes * MINUTE_MS;
}

/** Half-open intervals: one ending exactly when another starts does not overlap it. */
export function overlapsAny(interval: Interval, busy: readonly Interval[]): boolean {
  return busy.some((other) => interval.start < other.end && other.start < interval.end);
}

export function clampDuration(minutes: number): number {
  const aligned = Math.round(minutes / SLOT_MINUTES) * SLOT_MINUTES;
  return Math.min(MAX_BOOKING_MINUTES, Math.max(MIN_BOOKING_MINUTES, aligned));
}

/** Estimate only; the booking's `price_kzt` from the server is what is charged. */
export function estimatePriceKzt(pricePerHourKzt: number, minutes: number): number {
  return Math.round((pricePerHourKzt * minutes) / 60);
}
