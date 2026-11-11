import assert from 'node:assert/strict';
import { test } from 'node:test';

import { isValidIin } from './iin.ts';

// Generated with backend/app/domain/iin.py build_iin(), so both sides agree.
const VALID = ['000115500018', '950730400429', '100305500071', '881231412348'];

test('accepts IINs with a correct check digit', () => {
  for (const iin of VALID) assert.equal(isValidIin(iin), true, iin);
});

test('rejects every wrong check digit', () => {
  for (const iin of VALID) {
    for (let digit = 0; digit <= 9; digit++) {
      const candidate = iin.slice(0, 11) + digit;
      assert.equal(isValidIin(candidate), candidate === iin, candidate);
    }
  }
});

test('rejects a single mistyped digit', () => {
  assert.equal(isValidIin('000115500019'), false);
  assert.equal(isValidIin('000115600018'), false);
});

test('rejects anything that is not exactly 12 digits', () => {
  for (const value of ['', '00011550001', '0001155000180', '00011550001a', ' 000115500018', '०००११५५०००१८']) {
    assert.equal(isValidIin(value), false, JSON.stringify(value));
  }
});

test('uses the second weight row when the first pass gives 10', () => {
  // The 10th digit has weight 10 in the first row, so a lone 1 there gives exactly 10.
  const digits = [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0];
  // In the second row (3..11,1,2) the 10th and 11th digits have weights 1 and 2.
  const second = (1 * digits[9] + 2 * digits[10]) % 11;
  const iin = digits.join('') + second;
  assert.equal(isValidIin(iin), true, iin);
  assert.equal(isValidIin(digits.join('') + ((second + 1) % 10)), false);
});

test('rejects a number whose both passes give 10', () => {
  // Brute-force one such prefix and check that no check digit makes it valid.
  const w1 = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11];
  const w2 = [3, 4, 5, 6, 7, 8, 9, 10, 11, 1, 2];
  let found: string | null = null;
  for (let n = 0; n < 100_000 && found === null; n++) {
    const prefix = String(n).padStart(11, '0');
    const d = Array.from(prefix, Number);
    const pass = (w: number[]) => w.reduce((s, weight, i) => s + weight * d[i], 0) % 11;
    if (pass(w1) === 10 && pass(w2) === 10) found = prefix;
  }
  assert.notEqual(found, null);
  for (let digit = 0; digit <= 9; digit++) assert.equal(isValidIin(found! + digit), false);
});
