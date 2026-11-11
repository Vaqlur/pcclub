import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  clampDuration,
  daySlotStarts,
  estimatePriceKzt,
  openingHours,
  overlapsAny,
  slotEnd,
} from './slots.ts';
import { addDays, dateKey, formatTime, fromZoned, toZoned, weekday } from './time.ts';

const ALMATY = 'Asia/Almaty'; // UTC+5, no DST
const HOUR = 3_600_000;

test('toZoned shows the club clock, not UTC', () => {
  const noonAlmaty = Date.UTC(2026, 5, 1, 7, 0);
  assert.deepEqual(toZoned(noonAlmaty, ALMATY), { year: 2026, month: 6, day: 1, hour: 12, minute: 0 });
  assert.equal(formatTime(noonAlmaty, ALMATY), '12:00');
});

test('toZoned crosses the date line at club midnight', () => {
  const justBefore = Date.UTC(2026, 5, 1, 18, 59);
  const midnight = Date.UTC(2026, 5, 1, 19, 0);
  assert.equal(dateKey(toZoned(justBefore, ALMATY)), '2026-06-01');
  assert.deepEqual(toZoned(midnight, ALMATY), { year: 2026, month: 6, day: 2, hour: 0, minute: 0 });
});

test('fromZoned is the inverse of toZoned', () => {
  // Instants away from DST changes: a wall-clock time repeated by a clock change is ambiguous.
  for (const zone of [ALMATY, 'UTC', 'Europe/Berlin', 'America/New_York', 'Asia/Kolkata']) {
    for (const ms of [Date.UTC(2026, 0, 1, 0, 0), Date.UTC(2026, 5, 1, 7, 30), Date.UTC(2026, 9, 25, 12, 30)]) {
      assert.equal(fromZoned(toZoned(ms, zone), zone), ms, `${zone} ${ms}`);
    }
  }
});

test('fromZoned rolls hour 24 into the next day', () => {
  const endOfDay = fromZoned({ year: 2026, month: 6, day: 1, hour: 24, minute: 0 }, ALMATY);
  assert.equal(endOfDay, fromZoned({ year: 2026, month: 6, day: 2, hour: 0, minute: 0 }, ALMATY));
});

test('addDays and weekday work on calendar dates', () => {
  assert.equal(addDays('2026-06-30', 1), '2026-07-01');
  assert.equal(addDays('2026-12-31', 1), '2027-01-01');
  assert.equal(addDays('2028-02-28', 1), '2028-02-29');
  assert.equal(addDays('2026-06-01', 14), '2026-06-15');
  assert.equal(weekday('2026-06-01'), 1); // Monday
});

test('a 24/7 club has 48 half-hour starts, aligned on the club clock', () => {
  const starts = daySlotStarts('2026-06-01', ALMATY, null);
  assert.equal(starts.length, 48);
  assert.equal(formatTime(starts[0], ALMATY), '00:00');
  assert.equal(formatTime(starts[1], ALMATY), '00:30');
  assert.equal(formatTime(starts[47], ALMATY), '23:30');
  assert.equal(starts[0], Date.UTC(2026, 4, 31, 19, 0));
});

test('half-hour offsets stay aligned to the local clock', () => {
  const starts = daySlotStarts('2026-06-01', 'Asia/Kolkata', null); // UTC+5:30
  for (const start of starts) assert.equal(toZoned(start, 'Asia/Kolkata').minute % 30, 0);
});

test('opening hours limit the starts so the shortest booking still fits', () => {
  const starts = daySlotStarts('2026-06-01', ALMATY, openingHours('10:00:00', '23:00:00'));
  assert.equal(formatTime(starts[0], ALMATY), '10:00');
  assert.equal(formatTime(starts.at(-1)!, ALMATY), '22:00'); // 22:00-23:00 is the last full hour
  assert.equal(starts.length, 25);
});

test('an overnight club is open on both sides of midnight', () => {
  const labels = daySlotStarts('2026-06-01', ALMATY, openingHours('18:00', '04:00')).map((s) =>
    formatTime(s, ALMATY),
  );
  assert.equal(labels[0], '00:00');
  assert.ok(labels.includes('03:00'));
  assert.ok(!labels.includes('03:30')); // would end at 04:30
  assert.ok(!labels.includes('12:00'));
  assert.ok(labels.includes('18:00'));
  assert.equal(labels.at(-1), '23:30');
});

test('missing opening or closing time means open around the clock', () => {
  assert.equal(openingHours(null, null), null);
  assert.equal(openingHours('10:00:00', null), null);
});

test('overlap uses half-open intervals', () => {
  const busy = [{ start: 10 * HOUR, end: 12 * HOUR }];
  assert.equal(overlapsAny({ start: 8 * HOUR, end: 10 * HOUR }, busy), false); // ends at the start
  assert.equal(overlapsAny({ start: 12 * HOUR, end: 13 * HOUR }, busy), false); // starts at the end
  assert.equal(overlapsAny({ start: 9 * HOUR, end: 10 * HOUR + 1 }, busy), true);
  assert.equal(overlapsAny({ start: 11 * HOUR, end: 11.5 * HOUR }, busy), true);
  assert.equal(overlapsAny({ start: 9 * HOUR, end: 13 * HOUR }, busy), true);
  assert.equal(overlapsAny({ start: 9 * HOUR, end: 13 * HOUR }, []), false);
});

test('duration is clamped to 1-12 hours in half-hour steps', () => {
  assert.equal(clampDuration(30), 60);
  assert.equal(clampDuration(60), 60);
  assert.equal(clampDuration(90), 90);
  assert.equal(clampDuration(100), 90);
  assert.equal(clampDuration(720), 720);
  assert.equal(clampDuration(750), 720);
});

test('slot end and price estimate', () => {
  assert.equal(slotEnd(0, 90), 1.5 * HOUR);
  assert.equal(estimatePriceKzt(800, 60), 800);
  assert.equal(estimatePriceKzt(1500, 150), 3750);
  assert.equal(estimatePriceKzt(700, 90), 1050);
});
