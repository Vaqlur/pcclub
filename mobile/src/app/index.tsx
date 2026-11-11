import { useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { listClubs } from '@/api/endpoints';
import { useAuth, useUser } from '@/auth/AuthContext';
import { openingHoursLabel, t } from '@/i18n';
import { useLoad } from '@/lib/useLoad';
import { Button, Card, Loadable, Screen } from '@/ui/components';
import { colors, font, space } from '@/ui/theme';

/** Home: the clubs, plus the way to the user's bookings. */
export default function ClubsScreen() {
  const router = useRouter();
  const { signOut } = useAuth();
  const user = useUser();
  const clubs = useLoad(listClubs, 'clubs');

  return (
    <Screen>
      <Button
        title={t.clubs.myBookings}
        variant="secondary"
        onPress={() => router.push('/bookings')}
      />
      <Loadable state={clubs}>
        {(items) =>
          items.length === 0 ? (
            <Text style={font.small}>{t.clubs.empty}</Text>
          ) : (
            items.map((club) => (
              <Card
                key={club.id}
                onPress={() =>
                  router.push({ pathname: '/clubs/[clubId]', params: { clubId: club.id } })
                }
              >
                <Text style={font.heading}>{club.name}</Text>
                <Text style={font.small}>
                  {club.city}, {club.address}
                </Text>
                <Text style={font.small}>{openingHoursLabel(club)}</Text>
              </Card>
            ))
          )
        }
      </Loadable>
      <View style={styles.profile}>
        <Text style={font.small}>
          {[user.first_name, user.last_name].filter(Boolean).join(' ')} · {user.phone}
        </Text>
        {user.iin_masked ? (
          <Text style={font.small}>{t.clubs.verifiedAs(user.iin_masked)}</Text>
        ) : null}
        <Button title={t.common.signOut} variant="link" onPress={() => void signOut()} />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  profile: {
    marginTop: space.lg,
    paddingTop: space.lg,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    alignItems: 'center',
    gap: space.xs,
  },
});
