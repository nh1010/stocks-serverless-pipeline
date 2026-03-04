import { useCallback, useEffect, useState } from "react";
import type { Mover } from "../types";

async function getApiUrl(): Promise<string> {
  if (import.meta.env.VITE_API_URL) return import.meta.env.VITE_API_URL;
  const res = await fetch("/config.json");
  const config = await res.json();
  return config.apiUrl;
}

export function useMovers() {
  const [movers, setMovers] = useState<Mover[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const base = await getApiUrl();
      const res = await fetch(`${base}movers`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: Mover[] = await res.json();
      setMovers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  return { movers, loading, error, retry: load };
}
