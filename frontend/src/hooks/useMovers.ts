import { useQuery } from "@tanstack/react-query";
import type { MoversResponse } from "../types";

const API_URL = import.meta.env.VITE_API_URL as string;

async function fetchMovers(): Promise<MoversResponse> {
  const res = await fetch(`${API_URL}/movers`);
  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }
  return res.json();
}

export function useMovers() {
  return useQuery({
    queryKey: ["movers"],
    queryFn: fetchMovers,
    staleTime: 5 * 60 * 1000,
    retry: 2,
  });
}
