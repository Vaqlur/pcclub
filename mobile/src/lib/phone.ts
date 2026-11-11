/**
 * Kazakhstan phone numbers to E.164 (+7XXXXXXXXXX). Mirrors backend/app/domain/phone.py so a
 * typo is caught before the request; the server normalizes again.
 */
export function normalizePhone(raw: string): string | null {
  let value = raw.replace(/[\s\-()]/g, '');
  if (/^[78]\d{10}$/.test(value)) value = `+7${value.slice(1)}`;
  return /^\+7\d{10}$/.test(value) ? value : null;
}
