/**
 * Fetch-on-mount with loading / error / reload, the same for every page.
 * `deps` re-run the load (e.g. a filter); `reload()` re-runs it on demand
 * (after a change) without blanking what is already on screen.
 */
import { useCallback, useEffect, useRef, useState, type DependencyList } from 'react';

import { toApiError } from '../api/errors';

export function useLoad<T>(fn: () => Promise<T>, deps: DependencyList = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const seq = useRef(0);

  const reload = useCallback(async () => {
    const mine = ++seq.current;
    setError(null);
    try {
      const value = await fn();
      if (mine === seq.current) setData(value);
    } catch (e) {
      if (mine === seq.current) setError(toApiError(e).message);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { data, error, reload };
}
