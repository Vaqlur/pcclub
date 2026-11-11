import { useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { listClubs } from '@/api/endpoints';
import { useAuth, useUser } from '@/auth/AuthContext';
import { openingHoursLabel, t } from '@/i18n';
import { useLoad } from '@/lib/useLoad';
import { Button, Card, Chip, Loadable, Screen } from '@/ui/components';
import { space, useTheme } from '@/ui/theme';

/** Home: the clubs, plus the way to the user's bookings and profile/settings. */
export default function ClubsScreen() {
  const router = useRouter();
  const { signOut } = useAuth();
  const user = useUser();
  const { colors, font, mode, setTheme, toggleTheme } = useTheme();
  const clubs = useLoad(listClubs, 'clubs');

  const isRefreshing = clubs.loading && clubs.data !== null;

  return (
    <Screen refreshing={isRefreshing} onRefresh={clubs.reload}>
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
      <View style={[styles.profile, { borderTopColor: colors.border }]}>
        <Text style={font.small}>
          {[user.first_name, user.last_name].filter(Boolean).join(' ')} · {user.phone}
        </Text>
        {user.iin_masked ? (
          <Text style={font.small}>{t.clubs.verifiedAs(user.iin_masked)}</Text>
        ) : null}
        <View style={styles.themeSection}>
          <Text style={font.small}>{t.theme.label}</Text>
          <View style={styles.themeRow}>
            <Chip
              label={t.theme.light}
              selected={mode === 'light'}
              onPress={() => setTheme('light')}
            />
            <Chip
              label={t.theme.dark}
              selected={mode === 'dark'}
              onPress={() => setTheme('dark')}
            />
          </View>
          <Button
            title={mode === 'light' ? t.theme.switchToDark : t.theme.switchToLight}
            variant="link"
            onPress={toggleTheme}
          />
        </View>
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
    alignItems: 'center',
    gap: space.xs,
  },
  themeSection: {
    marginTop: space.sm,
    alignItems: 'center',
    gap: space.xs,
  },
  themeRow: {
    flexDirection: 'row',
    gap: space.sm,
  },
});
