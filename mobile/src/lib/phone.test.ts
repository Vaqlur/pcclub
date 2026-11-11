import assert from 'node:assert/strict';
import { test } from 'node:test';

import { normalizePhone } from './phone.ts';

test('normalizes the usual ways of writing a Kazakhstan number', () => {
  for (const raw of ['+7 707 123-45-67', '87071234567', '77071234567', '+7 (707) 123 45 67', '+77071234567']) {
    assert.equal(normalizePhone(raw), '+77071234567', raw);
  }
});

test('rejects numbers that are not +7 with 10 digits', () => {
  for (const raw of ['', '+7', '7071234567', '+7707123456', '+770712345678', '+17071234567', '97071234567', '+7707123456a']) {
    assert.equal(normalizePhone(raw), null, JSON.stringify(raw));
  }
});
