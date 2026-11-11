import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { AuthProvider, useAuth } from '@/auth/AuthContext';
import { errorMessage, t } from '@/i18n';
import { Button, Notice } from '@/ui/components';
import { ThemeProvider, space, useTheme } from '@/ui/theme';

/**
 * Three groups of screens, exactly one of which is reachable at a time:
 * signed out -> login; signed in without a verified IIN -> identity; verified -> the app.
 * Unverified users cannot book at all (the server enforces it), so the app does not let them in.
 */
function Navigator() {
  const { state, retry, signOut } = useAuth();
  const { colors, isDark } = useTheme();

  if (state.status === 'loading') {
    return (
      <View style={[styles.centered, { backgroundColor: colors.background }]}>
        <ActivityIndicator color={colors.primary} accessibilityLabel={t.common.loading} />
      </View>
    );
  }
  if (state.status === 'unreachable') {
    return (
      <View style={[styles.centered, { backgroundColor: colors.background }]}>
        <Notice>{errorMessage(state.error)}</Notice>
        <Button title={t.common.retry} onPress={retry} />
        <Button title={t.common.signOut} variant="link" onPress={() => void signOut()} />
      </View>
    );
  }

  const signedIn = state.status === 'signedIn';
  const verified = signedIn && state.user.identity_status === 'verified';

  return (
    <>
      <StatusBar style={isDark ? 'light' : 'dark'} />
      <Stack
        screenOptions={{
          headerTintColor: colors.primary,
          headerStyle: { backgroundColor: colors.surface },
          headerTitleStyle: { color: colors.text },
          headerBackTitle: t.common.back,
          contentStyle: { backgroundColor: colors.background },
        }}
      >
        <Stack.Protected guard={!signedIn}>
          <Stack.Screen name="login" options={{ title: t.login.title }} />
        </Stack.Protected>
        <Stack.Protected guard={signedIn && !verified}>
          <Stack.Screen name="identity" options={{ title: t.identity.title }} />
        </Stack.Protected>
        <Stack.Protected guard={verified}>
          <Stack.Screen name="index" options={{ title: t.clubs.title }} />
          <Stack.Screen name="clubs/[clubId]" options={{ title: '' }} />
          <Stack.Screen name="pcs/[pcId]" options={{ title: '' }} />
          <Stack.Screen name="bookings/index" options={{ title: t.bookings.title }} />
          <Stack.Screen name="bookings/[bookingId]" options={{ title: t.bookings.details }} />
        </Stack.Protected>
      </Stack>
    </>
  );
}

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <ThemeProvider>
        <AuthProvider>
          <Navigator />
        </AuthProvider>
      </ThemeProvider>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  centered: {
    flex: 1,
    justifyContent: 'center',
    padding: space.xl,
    gap: space.md,
  },
});
