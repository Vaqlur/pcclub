/**
 * Club-local time. Everything about "time of day" is evaluated in the club's IANA timezone,
 * never the phone's. Instants are epoch milliseconds; wall-clock values are LocalDateTime.
 * Pure functions (the timezone database comes from Intl).
 */

export type LocalDateTime = {
  year: number;
  month: number; // 1-12
  day: number;
  hour: number;
  minute: number;
};

const formatters = new Map<string, Intl.DateTimeFormat>();

function formatterFor(timeZone: string): Intl.DateTimeFormat {
  let formatter = formatters.get(timeZone);
  if (!formatter) {
    formatter = new Intl.DateTimeFormat('en-US', {
      timeZone,
      hourCycle: 'h23',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
    formatters.set(timeZone, formatter);
  }
  return formatter;
}

/** Wall-clock time in `timeZone` at the instant `ms`. */
export function toZoned(ms: number, timeZone: string): LocalDateTime {
  const parts: Record<string, number> = {};
  for (const part of formatterFor(timeZone).formatToParts(new Date(ms))) {
    if (part.type !== 'literal') parts[part.type] = Number(part.value);
  }
  return {
    year: parts.year,
    month: parts.month,
    day: parts.day,
    hour: parts.hour % 24, // some engines print midnight as 24
    minute: parts.minute,
  };
}

function asUtc(local: LocalDateTime): number {
  return Date.UTC(local.year, local.month - 1, local.day, local.hour, local.minute);
}

/** The instant at which clocks in `timeZone` show `local`. Hours past 23 roll into the next day. */
export function fromZoned(local: LocalDateTime, timeZone: string): number {
  const target = asUtc(local);
  let guess = target;
  // Two passes settle the offset even when the first guess lands across an offset change.
  for (let i = 0; i < 2; i++) {
    const offset = asUtc(toZoned(guess, timeZone)) - guess;
    guess = target - offset;
  }
  return guess;
}

const pad = (n: number) => String(n).padStart(2, '0');

/** `YYYY-MM-DD`, the format of the API's `date` parameters. */
export function dateKey(local: Pick<LocalDateTime, 'year' | 'month' | 'day'>): string {
  return `${local.year}-${pad(local.month)}-${pad(local.day)}`;
}

export function parseDateKey(key: string): Pick<LocalDateTime, 'year' | 'month' | 'day'> {
  const [year, month, day] = key.split('-').map(Number);
  return { year, month, day };
}

export function addDays(key: string, days: number): string {
  const { year, month, day } = parseDateKey(key);
  const shifted = new Date(Date.UTC(year, month - 1, day + days));
  return dateKey({
    year: shifted.getUTCFullYear(),
    month: shifted.getUTCMonth() + 1,
    day: shifted.getUTCDate(),
  });
}

/** Day of week of a calendar date, 0 = Sunday. */
export function weekday(key: string): number {
  const { year, month, day } = parseDateKey(key);
  return new Date(Date.UTC(year, month - 1, day)).getUTCDay();
}

/** `HH:MM` on the club's clock. */
export function formatTime(ms: number, timeZone: string): string {
  const local = toZoned(ms, timeZone);
  return `${pad(local.hour)}:${pad(local.minute)}`;
}

/** Minutes since midnight from the API's `HH:MM[:SS]` time strings. */
export function parseTimeOfDay(value: string): number {
  const [hour, minute] = value.split(':').map(Number);
  return hour * 60 + minute;
}
