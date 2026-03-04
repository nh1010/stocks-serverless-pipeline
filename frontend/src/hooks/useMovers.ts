import { useEffect, useState } from "react";
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

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const base = await getApiUrl();
        const res = await fetch(`${base}movers`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: Mover[] = await res.json();
        if (!cancelled) setMovers(data);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, []);

  return { movers, loading, error };
}
