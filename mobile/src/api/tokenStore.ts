/**
 * Where the session tokens live between app launches.
 * Native: the OS keystore via expo-secure-store. Web (dev preview only): localStorage, because
 * expo-secure-store has no web implementation.
 */

import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

const KEY = 'pcclub.session';

export type Tokens = { accessToken: string; refreshToken: string };

const isWeb = Platform.OS === 'web';

export async function readTokens(): Promise<Tokens | null> {
  try {
    const raw = isWeb ? globalThis.localStorage?.getItem(KEY) : await SecureStore.getItemAsync(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<Tokens>;
    if (typeof parsed.accessToken !== 'string' || typeof parsed.refreshToken !== 'string') {
      return null;
    }
    return { accessToken: parsed.accessToken, refreshToken: parsed.refreshToken };
  } catch {
    return null; // unreadable storage is the same as being signed out
  }
}

export async function writeTokens(tokens: Tokens | null): Promise<void> {
  try {
    if (tokens === null) {
      if (isWeb) globalThis.localStorage?.removeItem(KEY);
      else await SecureStore.deleteItemAsync(KEY);
      return;
    }
    const raw = JSON.stringify(tokens);
    if (isWeb) globalThis.localStorage?.setItem(KEY, raw);
    else await SecureStore.setItemAsync(KEY, raw);
  } catch {
    // The session still works in memory; the user just signs in again after a restart.
  }
}
