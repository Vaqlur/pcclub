import { useFocusEffect } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';

export type LoadState<T> = {
  data: T | null;
  error: unknown;
  loading: boolean;
  reload: () => void;
};

/**
 * Runs `load` on mount, whenever `key` changes, and each time the screen regains focus.
 * Results of superseded calls are dropped, so a slow old response never overwrites a newer one.
 * Data from the previous key is cleared; a refetch of the same key keeps showing the old data.
 */
export function useLoad<T>(load: () => Promise<T>, key: string): LoadState<T> {
  const [state, setState] = useState<{ key: string; data: T | null; error: unknown; loading: boolean }>(
    { key, data: null, error: null, loading: true },
  );
  const latest = useRef(0);
  const loadRef = useRef(load);
  useEffect(() => {
    loadRef.current = load;
  });

  const run = useCallback(() => {
    const call = ++latest.current;
    setState((previous) => ({
      key,
      data: previous.key === key ? previous.data : null,
      error: null,
      loading: true,
    }));
    loadRef.current().then(
      (data) => {
        if (call === latest.current) setState({ key, data, error: null, loading: false });
      },
      (error: unknown) => {
        if (call !== latest.current) return;
        setState((previous) => ({ key, data: previous.data, error, loading: false }));
      },
    );
  }, [key]);

  useFocusEffect(run);

  const current = state.key === key ? state : { data: null, error: null, loading: true };
  return { data: current.data, error: current.error, loading: current.loading, reload: run };
}
