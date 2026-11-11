import {
  type ReactNode,
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';

import {
  ApiError,
  currentRefreshToken,
  endSession,
  restoreSession,
  setSessionLostHandler,
  startSession,
} from '@/api/client';
import { type TokenPair, type User, getMe, logout } from '@/api/endpoints';

type AuthState =
  | { status: 'loading'; user: null; error: null }
  | { status: 'signedOut'; user: null; error: null }
  | { status: 'signedIn'; user: User; error: null }
  /** A stored session exists but the profile could not be loaded (e.g. no network). */
  | { status: 'unreachable'; user: null; error: unknown };

type AuthContextValue = {
  state: AuthState;
  /** Store the tokens from a successful OTP verification and load the profile. */
  signIn: (pair: TokenPair) => Promise<void>;
  signOut: () => Promise<void>;
  setUser: (user: User) => void;
  retry: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

const LOADING: AuthState = { status: 'loading', user: null, error: null };
const SIGNED_OUT: AuthState = { status: 'signedOut', user: null, error: null };

/** The profile behind the stored tokens. Never throws: failures become states. */
async function loadProfile(): Promise<AuthState> {
  try {
    return { status: 'signedIn', user: await getMe(), error: null };
  } catch (error) {
    // 401 here means the refresh was rejected too, so the session is gone.
    if (error instanceof ApiError && error.status === 401) return SIGNED_OUT;
    return { status: 'unreachable', user: null, error };
  }
}

async function loadSession(): Promise<AuthState> {
  return (await restoreSession()) ? loadProfile() : SIGNED_OUT;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(LOADING);

  useEffect(() => {
    let active = true;
    setSessionLostHandler(() => setState(SIGNED_OUT));
    void loadSession().then((next) => {
      if (active) setState(next);
    });
    return () => {
      active = false;
      setSessionLostHandler(null);
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      state,
      signIn: async (pair) => {
        await startSession(pair);
        setState(await loadProfile());
      },
      signOut: async () => {
        const refreshToken = currentRefreshToken();
        await endSession();
        setState(SIGNED_OUT);
        // Best effort: the local session is already gone even if the server cannot be reached.
        if (refreshToken) logout(refreshToken).catch(() => undefined);
      },
      setUser: (user) => setState({ status: 'signedIn', user, error: null }),
      retry: () => {
        setState(LOADING);
        void loadSession().then(setState);
      },
    }),
    [state],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside AuthProvider');
  return value;
}

/** The signed-in user, for screens that are only reachable when signed in. */
export function useUser(): User {
  const { state } = useAuth();
  if (state.status !== 'signedIn') throw new Error('useUser requires a signed-in user');
  return state.user;
}
