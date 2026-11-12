import { useEffect, useRef, useState } from "react";

// Calls `fetcher` now and then every `ms` milliseconds. Returns { data, error, reload }.
// This is how the dashboard "watches" the backend: the graph runs in the background,
// so the page simply asks again every few seconds.
export default function usePolling(fetcher, deps, ms = 3000) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const [tick, setTick] = useState(0);
  const reload = () => setTick((t) => t + 1);

  useEffect(() => {
    let stop = false;
    async function load() {
      try {
        const d = await fetcherRef.current();
        if (!stop) {
          setData(d);
          setError("");
        }
      } catch (e) {
        if (!stop) setError(e.message === "Failed to fetch" ? "Cannot reach the backend on port 8000. Is it running?" : e.message);
      }
    }
    load();
    const timer = setInterval(load, ms);
    return () => {
      stop = true;
      clearInterval(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick, ms]);

  return { data, error, reload };
}
