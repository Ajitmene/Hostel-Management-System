import { useCallback, useEffect, useRef, useState } from "react";
import { errorMessage } from "../utils/errors.js";

const clean = (obj) =>
  Object.fromEntries(Object.entries(obj).filter(([, v]) => v !== "" && v !== null && v !== undefined));

/** Loads a paginated list and re-loads when page or filters change. */
export function usePagedQuery(fetcher, initial = {}, pageSize = 10) {
  const [params, setParams] = useState({ page: 1, page_size: pageSize, ...initial });
  const [state, setState] = useState({ loading: true, error: null, data: null });
  const [tick, setTick] = useState(0);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const key = JSON.stringify(params);
  useEffect(() => {
    let cancelled = false;
    setState((s) => ({ ...s, loading: true, error: null }));
    fetcherRef
      .current(clean(params))
      .then((res) => !cancelled && setState({ loading: false, error: null, data: res.data }))
      .catch((e) => !cancelled && setState({ loading: false, error: errorMessage(e), data: null }));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, tick]);

  const update = useCallback((patch) => setParams((p) => ({ ...p, ...patch, page: 1 })), []);
  const setPage = useCallback((page) => setParams((p) => ({ ...p, page })), []);
  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { ...state, params, update, setPage, reload };
}

/** Loads a single resource (or any one-off request). */
export function useLoad(fn, deps = []) {
  const [state, setState] = useState({ loading: true, error: null, data: null });
  const [tick, setTick] = useState(0);
  const fnRef = useRef(fn);
  fnRef.current = fn;
  useEffect(() => {
    let cancelled = false;
    setState((s) => ({ ...s, loading: true, error: null }));
    fnRef
      .current()
      .then((res) => !cancelled && setState({ loading: false, error: null, data: res.data }))
      .catch((e) => !cancelled && setState({ loading: false, error: errorMessage(e), data: null }));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);
  return { ...state, reload: () => setTick((t) => t + 1) };
}
