import { Stack, useLocalSearchParams, useRouter } from 'expo-router';
import { useMemo, useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { ApiError } from '@/api/client';
import { createBooking, getClub, getPcAvailability, listPcs } from '@/api/endpoints';
import { errorMessage, formatDay, formatDuration, formatKzt, t } from '@/i18n';
import {
  MAX_ADVANCE_DAYS,
  MAX_BOOKING_MINUTES,
  MIN_BOOKING_MINUTES,
  SLOT_MINUTES,
  clampDuration,
  daySlotStarts,
  estimatePriceKzt,
  openingHours,
  overlapsAny,
  slotEnd,
} from '@/lib/slots';
import { addDays, dateKey, formatTime, toZoned } from '@/lib/time';
import { useLoad } from '@/lib/useLoad';
import { useNow } from '@/lib/useNow';
import { Button, Chip, Loadable, Notice, Screen } from '@/ui/components';
import { colors, font, radius, space } from '@/ui/theme';

/** Pick a day, a start and a duration on the club's clock, then hold the PC. */
export default function BookPcScreen() {
  const { pcId, clubId } = useLocalSearchParams<{ pcId: string; clubId: string }>();
  const router = useRouter();
  // Refreshed twice a minute, so past slots grey out while the screen stays open.
  const now = useNow(30_000);

  const [day, setDay] = useState<string | null>(null); // club-local YYYY-MM-DD; null = today
  const [start, setStart] = useState<number | null>(null);
  const [minutes, setMinutes] = useState(MIN_BOOKING_MINUTES);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const base = useLoad(async () => {
    const [club, pcs] = await Promise.all([getClub(clubId), listPcs(clubId)]);
    const pc = pcs.find((item) => item.id === pcId);
    if (!pc) throw new ApiError('NOT_FOUND', 'PC is not bookable', 404);
    return { club, pc };
  }, `book:${clubId}:${pcId}`);

  const timeZone = base.data?.club.timezone ?? null;
  const today = timeZone ? dateKey(toZoned(now, timeZone)) : null;
  const selectedDay = day ?? today;

  const availability = useLoad(
    async () => (selectedDay ? getPcAvailability(pcId, selectedDay) : null),
    `availability:${pcId}:${selectedDay}`,
  );

  const busy = useMemo(
    () =>
      (availability.data?.busy ?? []).map((interval) => ({
        start: Date.parse(interval.starts_at),
        end: Date.parse(interval.ends_at),
      })),
    [availability.data],
  );

  async function submit(startMs: number) {
    setSubmitting(true);
    setError(null);
    try {
      const booking = await createBooking({
        pc_id: pcId,
        starts_at: new Date(startMs).toISOString(),
        ends_at: new Date(slotEnd(startMs, minutes)).toISOString(),
      });
      router.replace({ pathname: '/bookings/[bookingId]', params: { bookingId: booking.id } });
    } catch (caught) {
      setError(errorMessage(caught));
      availability.reload(); // the slot may just have been taken
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Screen>
      <Stack.Screen
        options={{ title: base.data ? t.booking.title(base.data.pc.label) : '' }}
      />
      <Loadable state={base}>
        {({ club, pc }) => {
          const zone = club.timezone;
          const days = Array.from({ length: MAX_ADVANCE_DAYS + 1 }, (_, i) => addDays(today!, i));
          const starts = daySlotStarts(
            selectedDay!,
            zone,
            openingHours(club.opens_at, club.closes_at),
          );
          const isFree = (slot: number) =>
            slot > now &&
            !overlapsAny({ start: slot, end: slotEnd(slot, SLOT_MINUTES) }, busy);
          const selection =
            start === null ? null : { start, end: slotEnd(start, minutes) };
          const conflict = selection !== null && overlapsAny(selection, busy);
          const inPast = selection !== null && selection.start <= now;

          return (
            <>
              <Text style={font.small}>
                {pc.zone_name} · {formatKzt(pc.price_per_hour_kzt)} {t.common.perHour}
              </Text>

              <Text style={font.heading}>{t.booking.day}</Text>
              <ScrollView
                horizontal
                showsHorizontalScrollIndicator={false}
                contentContainerStyle={styles.dayRow}
              >
                {days.map((key, index) => (
                  <Chip
                    key={key}
                    label={
                      index === 0 ? t.booking.today : index === 1 ? t.booking.tomorrow : formatDay(key)
                    }
                    selected={key === selectedDay}
                    onPress={() => {
                      setDay(key);
                      setStart(null);
                      setError(null);
                    }}
                  />
                ))}
              </ScrollView>

              <Text style={font.heading}>{t.booking.start}</Text>
              <Text style={font.small}>{t.booking.clubTime(zone)}</Text>
              {availability.error ? (
                <Notice>{errorMessage(availability.error)}</Notice>
              ) : availability.data === null ? (
                <Text style={font.small}>{t.common.loading}</Text>
              ) : starts.some(isFree) ? (
                <View style={styles.slotGrid}>
                  {starts.map((slot) => {
                    const inSelection =
                      selection !== null && slot >= selection.start && slot < selection.end;
                    return (
                      <View key={slot} style={inSelection && slot !== start ? styles.inRange : null}>
                        <Chip
                          label={formatTime(slot, zone)}
                          selected={slot === start}
                          disabled={!isFree(slot)}
                          onPress={() => {
                            setStart(slot);
                            setError(null);
                          }}
                        />
                      </View>
                    );
                  })}
                </View>
              ) : (
                <Text style={font.small}>{t.booking.noSlots}</Text>
              )}

              <Text style={font.heading}>{t.booking.duration}</Text>
              <View style={styles.stepper}>
                <Button
                  title="−"
                  accessibilityLabel={t.booking.shorter}
                  variant="secondary"
                  disabled={minutes <= MIN_BOOKING_MINUTES}
                  onPress={() => setMinutes((value) => clampDuration(value - SLOT_MINUTES))}
                />
                <Text style={styles.duration}>{formatDuration(minutes)}</Text>
                <Button
                  title="+"
                  accessibilityLabel={t.booking.longer}
                  variant="secondary"
                  disabled={minutes >= MAX_BOOKING_MINUTES}
                  onPress={() => setMinutes((value) => clampDuration(value + SLOT_MINUTES))}
                />
              </View>

              <View style={styles.summary}>
                {selection === null ? (
                  <Text style={font.small}>{t.booking.pickStart}</Text>
                ) : (
                  <>
                    <Text style={font.body}>
                      {formatDay(dateKey(toZoned(selection.start, zone)))},{' '}
                      {formatTime(selection.start, zone)}–{formatTime(selection.end, zone)}
                    </Text>
                    <Text style={font.small}>
                      {t.booking.estimate} {formatKzt(estimatePriceKzt(pc.price_per_hour_kzt, minutes))}
                    </Text>
                  </>
                )}
              </View>
              {conflict ? <Notice tone="warning">{t.booking.busyInRange}</Notice> : null}
              {error ? <Notice>{error}</Notice> : null}
              <Button
                title={t.booking.submit}
                disabled={selection === null || conflict || inPast}
                loading={submitting}
                onPress={() => {
                  if (selection) void submit(selection.start);
                }}
              />
            </>
          );
        }}
      </Loadable>
    </Screen>
  );
}

const styles = StyleSheet.create({
  dayRow: { gap: space.sm, paddingVertical: space.xs },
  slotGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: space.sm },
  inRange: { borderRadius: radius.sm, backgroundColor: colors.primarySoft },
  stepper: { flexDirection: 'row', alignItems: 'center', gap: space.lg },
  duration: { ...font.heading, minWidth: 110, textAlign: 'center' },
  summary: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: space.lg,
    gap: space.xs,
  },
});
