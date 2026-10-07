import { useEffect, useState } from "react";
import { fetchPublicSnapshot } from "../api/client.js";

export function usePublicSnapshot() {
  const [state, setState] = useState({
    snapshot: null,
    loading: true,
    error: null,
    source: "loading"
  });

  useEffect(() => {
    let cancelled = false;

    fetchPublicSnapshot()
      .then(({ data, source }) => {
        if (!cancelled) {
          setState({ snapshot: data, loading: false, error: null, source });
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setState({ snapshot: null, loading: false, error, source: "error" });
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
