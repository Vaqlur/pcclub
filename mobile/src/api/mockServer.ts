import type { components } from './schema';

type Schemas = components['schemas'];
type Club = Schemas['ClubOut'];
type Zone = Schemas['ZoneOut'];
type Pc = Schemas['PcOut'];
type Booking = Schemas['BookingOut'];
type Payment = Schemas['PaymentOut'];
type User = Schemas['UserOut'];
type TokenPair = Schemas['TokenPair'];

const DEMO_CLUBS: Club[] = [
  {
    id: '01900000-0000-7000-8000-000000000001',
    name: 'CyberArena Almaty',
    city: 'Алматы',
    address: 'пр. Абая, 44',
    timezone: 'Asia/Almaty',
    opens_at: null,
    closes_at: null,
  },
  {
    id: '01900000-0000-7000-8000-000000000002',
    name: 'Respawn Pro Club',
    city: 'Алматы',
    address: 'ул. Сатпаева, 22',
    timezone: 'Asia/Almaty',
    opens_at: '10:00:00',
    closes_at: '23:00:00',
  },
  {
    id: '01900000-0000-7000-8000-000000000003',
    name: 'Qazaq Esports Hub',
    city: 'Астана',
    address: 'пр. Мангилик Ел, 55/2',
    timezone: 'Asia/Almaty',
    opens_at: null,
    closes_at: null,
  },
];

const DEMO_ZONES: Zone[] = [
  {
    id: '01900000-0000-7000-8000-000000000101',
    club_id: '01900000-0000-7000-8000-000000000001',
    name: 'Standard',
    price_per_hour_kzt: 1000,
  },
  {
    id: '01900000-0000-7000-8000-000000000102',
    club_id: '01900000-0000-7000-8000-000000000001',
    name: 'VIP Bootcamp',
    price_per_hour_kzt: 1800,
  },
  {
    id: '01900000-0000-7000-8000-000000000201',
    club_id: '01900000-0000-7000-8000-000000000002',
    name: 'Pro Stage',
    price_per_hour_kzt: 1500,
  },
  {
    id: '01900000-0000-7000-8000-000000000301',
    club_id: '01900000-0000-7000-8000-000000000003',
    name: 'Arena 360Hz',
    price_per_hour_kzt: 1600,
  },
];

const DEMO_PCS: Pc[] = [
  {
    id: '01900000-0000-7000-8000-000000001001',
    club_id: '01900000-0000-7000-8000-000000000001',
    zone_id: '01900000-0000-7000-8000-000000000101',
    zone_name: 'Standard',
    label: 'PC-01',
    specs: { gpu: 'RTX 4060 Ti', monitor: '240 Hz', cpu: 'i5-13600K' },
    price_per_hour_kzt: 1000,
    available: true,
  },
  {
    id: '01900000-0000-7000-8000-000000001002',
    club_id: '01900000-0000-7000-8000-000000000001',
    zone_id: '01900000-0000-7000-8000-000000000102',
    zone_name: 'VIP Bootcamp',
    label: 'VIP-01',
    specs: { gpu: 'RTX 4080 Super', monitor: '360 Hz', cpu: 'Ryzen 7 7800X3D' },
    price_per_hour_kzt: 1800,
    available: true,
  },
  {
    id: '01900000-0000-7000-8000-000000002001',
    club_id: '01900000-0000-7000-8000-000000000002',
    zone_id: '01900000-0000-7000-8000-000000000201',
    zone_name: 'Pro Stage',
    label: 'PRO-01',
    specs: { gpu: 'RTX 4070 Super', monitor: '280 Hz', cpu: 'i7-14700K' },
    price_per_hour_kzt: 1500,
    available: true,
  },
  {
    id: '01900000-0000-7000-8000-000000003001',
    club_id: '01900000-0000-7000-8000-000000000003',
    zone_id: '01900000-0000-7000-8000-000000000301',
    zone_name: 'Arena 360Hz',
    label: 'ARENA-01',
    specs: { gpu: 'RTX 4080', monitor: '360 Hz', cpu: 'Ryzen 7 7800X3D' },
    price_per_hour_kzt: 1600,
    available: true,
  },
];

let currentUser: User = {
  id: '01900000-0000-7000-8000-000000009999',
  phone: '+77071234567',
  first_name: 'Алихан',
  last_name: 'Сатпаев',
  birth_date: '1999-05-15',
  identity_status: 'verified',
  iin_masked: '990515******',
};

const bookings: Booking[] = [
  {
    id: '01900000-0000-7000-8000-000000050001',
    user_id: currentUser.id,
    pc_id: '01900000-0000-7000-8000-000000001002',
    club_id: '01900000-0000-7000-8000-000000000001',
    starts_at: new Date(Date.now() + 2 * 3600_000).toISOString(),
    ends_at: new Date(Date.now() + 4 * 3600_000).toISOString(),
    status: 'confirmed',
    hold_expires_at: null,
    price_kzt: 3600,
    created_at: new Date(Date.now() - 1800_000).toISOString(),
    cancelled_at: null,
  },
];

const payments = new Map<string, Payment>();
let idCounter = 10;

export function handleMockApi<T>(
  method: 'GET' | 'POST' | 'PATCH',
  path: string,
  body?: unknown,
  query?: Record<string, string | number | null | undefined>,
): T {
  if (method === 'POST' && path === '/v1/auth/otp/request') {
    const payload = (body ?? {}) as { phone?: string };
    if (payload.phone) {
      currentUser = { ...currentUser, phone: payload.phone };
    }
    return undefined as T;
  }

  if (method === 'POST' && path === '/v1/auth/otp/verify') {
    const pair: TokenPair = {
      access_token: 'demo-access-token',
      refresh_token: 'demo-refresh-token',
      token_type: 'bearer',
      expires_in: 1800,
    };
    return pair as T;
  }

  if (method === 'POST' && path === '/v1/auth/logout') {
    return undefined as T;
  }

  if (method === 'GET' && path === '/v1/me') {
    return currentUser as T;
  }

  if (method === 'POST' && path === '/v1/me/identity') {
    const payload = (body ?? {}) as { iin?: string; first_name?: string; last_name?: string };
    const iin = payload.iin ?? '990515500018';
    currentUser = {
      ...currentUser,
      first_name: payload.first_name ?? currentUser.first_name,
      last_name: payload.last_name ?? currentUser.last_name,
      identity_status: 'verified',
      iin_masked: `${iin.slice(0, 6)}******`,
    };
    return currentUser as T;
  }

  if (method === 'GET' && path === '/v1/clubs') {
    return [...DEMO_CLUBS] as T;
  }

  const clubZonesMatch = /^\/v1\/clubs\/([^/]+)\/zones$/.exec(path);
  if (method === 'GET' && clubZonesMatch) {
    const clubId = clubZonesMatch[1];
    return DEMO_ZONES.filter((z) => z.club_id === clubId) as T;
  }

  const clubPcsMatch = /^\/v1\/clubs\/([^/]+)\/pcs$/.exec(path);
  if (method === 'GET' && clubPcsMatch) {
    const clubId = clubPcsMatch[1];
    return DEMO_PCS.filter((p) => p.club_id === clubId) as T;
  }

  const clubMatch = /^\/v1\/clubs\/([^/]+)$/.exec(path);
  if (method === 'GET' && clubMatch) {
    const club = DEMO_CLUBS.find((c) => c.id === clubMatch[1]) ?? DEMO_CLUBS[0];
    return club as T;
  }

  const availMatch = /^\/v1\/pcs\/([^/]+)\/availability$/.exec(path);
  if (method === 'GET' && availMatch) {
    const pcId = availMatch[1];
    const pc = DEMO_PCS.find((p) => p.id === pcId) ?? DEMO_PCS[0];
    const club = DEMO_CLUBS.find((c) => c.id === pc.club_id) ?? DEMO_CLUBS[0];
    const date = String(query?.date ?? new Date().toISOString().slice(0, 10));
    const busy = bookings
      .filter(
        (b) =>
          b.pc_id === pcId &&
          (b.status === 'confirmed' || b.status === 'pending_payment'),
      )
      .map((b) => ({ starts_at: b.starts_at, ends_at: b.ends_at }));
    return {
      pc_id: pcId,
      date,
      timezone: club.timezone,
      busy,
    } as T;
  }

  if (method === 'GET' && path === '/v1/bookings') {
    return {
      items: [...bookings],
      next_cursor: null,
    } as T;
  }

  if (method === 'POST' && path === '/v1/bookings') {
    const payload = (body ?? {}) as Schemas['BookingCreate'];
    const pc = DEMO_PCS.find((p) => p.id === payload.pc_id) ?? DEMO_PCS[0];
    const durationHours =
      (Date.parse(payload.ends_at) - Date.parse(payload.starts_at)) / 3600_000;
    const booking: Booking = {
      id: `01900000-0000-7000-8000-0000000500${++idCounter}`,
      user_id: currentUser.id,
      pc_id: pc.id,
      club_id: pc.club_id,
      starts_at: payload.starts_at,
      ends_at: payload.ends_at,
      status: 'pending_payment',
      hold_expires_at: new Date(Date.now() + 10 * 60_000).toISOString(),
      price_kzt: Math.round(pc.price_per_hour_kzt * Math.max(1, durationHours)),
      created_at: new Date().toISOString(),
      cancelled_at: null,
    };
    bookings.unshift(booking);
    return booking as T;
  }

  const cancelMatch = /^\/v1\/bookings\/([^/]+)\/cancel$/.exec(path);
  if (method === 'POST' && cancelMatch) {
    const booking = bookings.find((b) => b.id === cancelMatch[1]) ?? bookings[0];
    if (booking) {
      booking.status = 'cancelled';
      booking.cancelled_at = new Date().toISOString();
    }
    return booking as T;
  }

  const paymentCreateMatch = /^\/v1\/bookings\/([^/]+)\/payments$/.exec(path);
  if (method === 'POST' && paymentCreateMatch) {
    const booking = bookings.find((b) => b.id === paymentCreateMatch[1]) ?? bookings[0];
    const payload = (body ?? {}) as { method?: 'card' | 'kaspi' };
    const payment: Payment = {
      id: `01900000-0000-7000-8000-0000000800${++idCounter}`,
      booking_id: booking.id,
      method: payload.method ?? 'card',
      amount_kzt: booking.price_kzt,
      status: 'pending',
      redirect_url: null,
    };
    payments.set(payment.id, payment);
    return payment as T;
  }

  const bookingMatch = /^\/v1\/bookings\/([^/]+)$/.exec(path);
  if (method === 'GET' && bookingMatch) {
    const booking = bookings.find((b) => b.id === bookingMatch[1]) ?? bookings[0];
    return booking as T;
  }

  const mockPayMatch = /^\/v1\/payments\/mock\/([^/]+)\/(complete|fail)$/.exec(path);
  if (method === 'POST' && mockPayMatch) {
    const payment = payments.get(mockPayMatch[1]);
    const outcome = mockPayMatch[2];
    if (payment) {
      payment.status = outcome === 'complete' ? 'succeeded' : 'failed';
      if (outcome === 'complete') {
        const booking = bookings.find((b) => b.id === payment.booking_id);
        if (booking) {
          booking.status = 'confirmed';
          booking.hold_expires_at = null;
        }
      }
      return payment as T;
    }
  }

  return undefined as T;
}
