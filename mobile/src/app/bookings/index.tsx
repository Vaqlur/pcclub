import { useRouter } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { type Booking, listBookings, listClubs } from '@/api/endpoints';
import { errorMessage, formatInstantDay, formatKzt, t } from '@/i18n';
import { formatTime } from '@/lib/time';
import { useLoad } from '@/lib/useLoad';
import { Button, Card, Loadable, Notice, Screen } from '@/ui/components';
import { StatusBadge } from '@/ui/StatusBadge';
import { font, space } from '@/ui/theme';

const FALLBACK_ZONE = 'Asia/Almaty';

/** Booking history, newest first. Times are shown on each club's own clock. */
export default function BookingsScreen() {
  const router = useRouter();
  // Pages after the first, appended by "show more". Reset whenever the first page reloads.
  const [extra, setExtra] = useState<{ items: Booking[]; cursor: string | null } | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [moreError, setMoreError] = useState<string | null>(null);

  const state = useLoad(async () => {
    const [page, clubs] = await Promise.all([listBookings(), listClubs()]);
    setExtra(null);
    return { page, clubs: new Map(clubs.map((club) => [club.id, club])) };
  }, 'bookings');

  async function loadMore(cursor: string) {
    setLoadingMore(true);
    setMoreError(null);
    try {
      const page = await listBookings(cursor);
      setExtra((previous) => ({
        items: [...(previous?.items ?? []), ...page.items],
        cursor: page.next_cursor,
      }));
    } catch (caught) {
      setMoreError(errorMessage(caught));
    } finally {
      setLoadingMore(false);
    }
  }

  return (
    <Screen>
      <Loadable state={state}>
        {({ page, clubs }) => {
          const items = [...page.items, ...(extra?.items ?? [])];
          const cursor = extra ? extra.cursor : page.next_cursor;
          if (items.length === 0) return <Text style={font.small}>{t.bookings.empty}</Text>;
          return (
            <>
              {items.map((booking) => {
                const club = clubs.get(booking.club_id);
                const zone = club?.timezone ?? FALLBACK_ZONE;
                const start = Date.parse(booking.starts_at);
                const end = Date.parse(booking.ends_at);
                return (
                  <Card
                    key={booking.id}
                    onPress={() =>
                      router.push({
                        pathname: '/bookings/[bookingId]',
                        params: { bookingId: booking.id },
                      })
                    }
                  >
                    <View style={styles.header}>
                      <Text style={[font.heading, styles.title]}>{club?.name ?? '—'}</Text>
                      <StatusBadge status={booking.status} />
                    </View>
                    <Text style={font.body}>
                      {formatInstantDay(start, zone)}, {formatTime(start, zone)}–
                      {formatTime(end, zone)}
                    </Text>
                    <Text style={font.small}>{formatKzt(booking.price_kzt)}</Text>
                  </Card>
                );
              })}
              {moreError ? <Notice>{moreError}</Notice> : null}
              {cursor ? (
                <Button
                  title={t.bookings.more}
                  variant="secondary"
                  loading={loadingMore}
                  onPress={() => void loadMore(cursor)}
                />
              ) : null}
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
});
