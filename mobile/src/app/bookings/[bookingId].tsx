import * as Crypto from 'expo-crypto';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import {
  type Booking,
  type Payment,
  type PaymentMethod,
  cancelBooking,
  createPayment,
  getBooking,
  getClub,
  listPcs,
  simulateMockPayment,
} from '@/api/endpoints';
import { errorMessage, formatCountdown, formatInstantDay, formatKzt, t } from '@/i18n';
import { formatTime } from '@/lib/time';
import { useLoad } from '@/lib/useLoad';
import { useNow } from '@/lib/useNow';
import { Button, Card, Chip, Loadable, Notice, Row, Screen } from '@/ui/components';
import { StatusBadge } from '@/ui/StatusBadge';
import { font, space } from '@/ui/theme';

const METHODS: PaymentMethod[] = ['card', 'kaspi'];

/**
 * Pay for a held booking through the mock provider.
 *
 * The app only starts the payment and (in development) tells the mock provider which webhook to
 * send. The booking becomes confirmed on the server when that webhook arrives; the app then
 * re-reads the booking and never marks it paid itself.
 */
function PaymentPanel({ booking, onChanged }: { booking: Booking; onChanged: () => void }) {
  const [method, setMethod] = useState<PaymentMethod>('card');
  const [payment, setPayment] = useState<Payment | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // One Idempotency-Key per payment attempt and method: a retry after a network error reuses
  // it and gets the original payment back instead of creating a second one.
  const keys = useRef(new Map<PaymentMethod, string>());

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (caught) {
      setError(errorMessage(caught));
      onChanged(); // e.g. the hold ran out: show the booking's real state
    } finally {
      setBusy(false);
    }
  }

  function start() {
    void run(async () => {
      let key = keys.current.get(method);
      if (!key) {
        key = Crypto.randomUUID();
        keys.current.set(method, key);
      }
      setPayment(await createPayment(booking.id, method, key));
    });
  }

  function simulate(outcome: 'complete' | 'fail') {
    if (!payment) return;
    void run(async () => {
      const result = await simulateMockPayment(payment.id, outcome);
      if (result.status === 'failed') {
        keys.current.delete(payment.method as PaymentMethod); // the next attempt is a new payment
        setPayment(null);
        setError(t.payment.failed);
      }
      onChanged();
    });
  }

  return (
    <Card>
      <Text style={font.heading}>{t.payment.title}</Text>
      {payment === null ? (
        <>
          <View style={styles.methods}>
            {METHODS.map((item) => (
              <Chip
                key={item}
                label={t.payment.method[item]}
                selected={item === method}
                disabled={busy}
                onPress={() => setMethod(item)}
              />
            ))}
          </View>
          {error ? <Notice>{error}</Notice> : null}
          <Button
            title={t.payment.pay(formatKzt(booking.price_kzt))}
            onPress={start}
            loading={busy}
          />
        </>
      ) : (
        <>
          <Notice tone="info">
            {t.payment.mockTitle}: {formatKzt(payment.amount_kzt)}. {t.payment.mockHint}
          </Notice>
          {error ? <Notice>{error}</Notice> : null}
          <Button
            title={t.payment.mockSucceed}
            onPress={() => simulate('complete')}
            loading={busy}
          />
          <Button
            title={t.payment.mockFail}
            variant="secondary"
            onPress={() => simulate('fail')}
            disabled={busy}
          />
        </>
      )}
    </Card>
  );
}

export default function BookingScreen() {
  const { bookingId } = useLocalSearchParams<{ bookingId: string }>();
  const router = useRouter();
  const [confirmingCancel, setConfirmingCancel] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);

  const state = useLoad(async () => {
    const booking = await getBooking(bookingId);
    const [club, pcs] = await Promise.all([
      getClub(booking.club_id),
      listPcs(booking.club_id).catch(() => []),
    ]);
    return { booking, club, pc: pcs.find((pc) => pc.id === booking.pc_id) ?? null };
  }, `booking:${bookingId}`);

  const booking = state.data?.booking ?? null;
  const holdDeadline =
    booking?.status === 'pending_payment' && booking.hold_expires_at
      ? Date.parse(booking.hold_expires_at)
      : null;
  const now = useNow(1000);
  const holdLeft = holdDeadline === null ? null : Math.max(0, holdDeadline - now);
  const holdOver = holdLeft === 0;

  // When the hold runs out, ask the server: it expires unpaid holds lazily on read.
  const reload = state.reload;
  useEffect(() => {
    if (holdOver) reload();
  }, [holdOver, reload]);

  async function cancel() {
    setCancelling(true);
    setCancelError(null);
    try {
      await cancelBooking(bookingId);
    } catch (caught) {
      setCancelError(errorMessage(caught));
    } finally {
      setCancelling(false);
      setConfirmingCancel(false);
      reload();
    }
  }

  return (
    <Screen>
      <Loadable state={state}>
        {({ booking: current, club, pc }) => {
          const zone = club.timezone;
          const start = Date.parse(current.starts_at);
          const end = Date.parse(current.ends_at);
          const pending = current.status === 'pending_payment';
          const cancellable =
            (pending || current.status === 'confirmed') && start > now;
          return (
            <>
              <Card>
                <View style={styles.header}>
                  <Text style={[font.heading, styles.title]}>
                    {[club.name, pc?.label].filter(Boolean).join(' · ')}
                  </Text>
                  <StatusBadge status={current.status} />
                </View>
                <Text style={font.small}>
                  {club.city}, {club.address}
                </Text>
                <Row
                  label={t.bookings.time}
                  value={`${formatInstantDay(start, zone)}, ${formatTime(start, zone)}–${formatTime(end, zone)}`}
                />
                <Row label={t.bookings.price} value={formatKzt(current.price_kzt)} />
              </Card>

              {pending && holdLeft !== null && !holdOver ? (
                <>
                  <Notice tone="warning">{t.bookings.holdLeft(formatCountdown(holdLeft))}</Notice>
                  <PaymentPanel booking={current} onChanged={reload} />
                </>
              ) : null}
              {pending && holdOver ? <Notice tone="warning">{t.bookings.holdExpired}</Notice> : null}
              {current.status === 'confirmed' ? (
                <Notice tone="success">{t.payment.succeeded}</Notice>
              ) : null}

              {cancelError ? <Notice>{cancelError}</Notice> : null}
              {cancellable ? (
                <Button
                  title={confirmingCancel ? t.bookings.cancelConfirm : t.bookings.cancel}
                  variant="danger"
                  loading={cancelling}
                  onPress={() => (confirmingCancel ? void cancel() : setConfirmingCancel(true))}
                />
              ) : null}
              <Button
                title={t.bookings.bookAgain}
                variant="link"
                onPress={() => router.dismissTo('/')}
              />
            </>
          );
        }}
      </Loadable>
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: 'row', justifyContent: 'space-between', gap: space.md },
  title: { flexShrink: 1 },
  methods: { flexDirection: 'row', gap: space.sm },
});
