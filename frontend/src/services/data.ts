// Two run modes, one codebase (see README "Frontend"):
// - Local dev: VITE_API_URL points at the FastAPI service (docker-compose
//   sets it) and data comes from /deals + /omissions.
// - Static production build: no API at all — the prebuild step copied the
//   committed snapshot into /data/*.json and we fetch those as plain files.
import type { Deal, Omission } from "../types";

const API_URL: string | undefined = import.meta.env.VITE_API_URL;

// Vite fills this with the configured `base`, always with a trailing slash.
// The snapshot paths have to be relative to it: on GitHub Pages the site
// lives under /tombstone/, where an absolute "/data/snapshot.json" resolves
// to the domain root and 404s.
const BASE = import.meta.env.BASE_URL;

async function fetchJson<T>(url: string, fallback: T): Promise<T> {
  try {
    const res = await fetch(url);
    if (!res.ok) return fallback;
    return (await res.json()) as T;
  } catch {
    return fallback;
  }
}

export async function loadDeals(): Promise<Deal[]> {
  const url = API_URL ? `${API_URL}/deals` : `${BASE}data/snapshot.json`;
  const deals = await fetchJson<Deal[]>(url, []);
  // Snapshots are files on disk that outlive the code reading them — one
  // written before `conflicts` existed is still perfectly valid data, and
  // the client may well open the dashboard against an older committed run.
  // Normalising here means the rest of the app can trust the type.
  return deals.map((deal) => ({
    ...deal,
    conflicts: deal.conflicts ?? [],
    valuation_estimate: deal.valuation_estimate ?? null,
  }));
}

export function loadOmissions(): Promise<Omission[]> {
  const url = API_URL ? `${API_URL}/omissions` : `${BASE}data/omissions.json`;
  return fetchJson<Omission[]>(url, []);
}

export const dataMode: "live-api" | "static-snapshot" = API_URL ? "live-api" : "static-snapshot";
