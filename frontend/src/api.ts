import type { Filters, Measurement, Series } from "./types";

export const MEASUREMENT_LIMIT = 10000;

async function getJson<T>(path: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(path, { signal });
  if (!response.ok) {
    const problem = await response.json().catch(() => null);
    throw new Error(problem?.detail || `Request failed (${response.status}).`);
  }
  return response.json();
}

export function getSeries(signal: AbortSignal) {
  return getJson<Series[]>("/api/series", signal);
}

export function getMeasurements(filters: Filters, signal: AbortSignal) {
  const query = new URLSearchParams({
    series: filters.seriesIds.join(","),
    sort: "timestamp",
    limit: String(MEASUREMENT_LIMIT),
  });
  if (filters.from) query.set("from", new Date(filters.from).toISOString());
  if (filters.to) query.set("to", new Date(filters.to).toISOString());
  return getJson<Measurement[]>(`/api/measurements?${query}`, signal);
}
