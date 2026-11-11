/**
 * Local IIN check: 12 digits and a valid check digit. This is only a filter to catch typos
 * before a network call; the server (and the identity registry behind it) is authoritative.
 *
 * Mirrors backend/app/domain/iin.py: weights 1..11 mod 11; if that gives 10, a second pass
 * with weights 3..11,1,2; if it is 10 again the number is not a valid IIN.
 */

const WEIGHTS_1 = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11];
const WEIGHTS_2 = [3, 4, 5, 6, 7, 8, 9, 10, 11, 1, 2];

export function isValidIin(iin: string): boolean {
  if (!/^\d{12}$/.test(iin)) return false;
  const digits = Array.from(iin, Number);
  for (const weights of [WEIGHTS_1, WEIGHTS_2]) {
    const remainder = weights.reduce((sum, weight, i) => sum + weight * digits[i], 0) % 11;
    if (remainder !== 10) return remainder === digits[11];
  }
  return false;
}
