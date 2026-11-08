import type {
  Filters,
  LoginResponse,
  Measurement,
  Series,
  SeriesInput,
  Sensor,
  RegisteredSensor,
} from "./types";

export const MEASUREMENT_LIMIT = 10000;

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, options);
  if (!response.ok) {
    const problem = await response.json().catch(() => null);
    throw new ApiError(
      response.status,
      problem?.detail || `Request failed (${response.status}).`,
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

export function getSeries(signal: AbortSignal) {
  return request<Series[]>("/api/series", { signal });
}

export function getMeasurements(filters: Filters, signal: AbortSignal) {
  const query = new URLSearchParams({
    series: filters.seriesIds.join(","),
    sort: "timestamp",
    limit: String(MEASUREMENT_LIMIT),
  });
  if (filters.from) query.set("from", new Date(filters.from).toISOString());
  if (filters.to) query.set("to", new Date(filters.to).toISOString());
  return request<Measurement[]>(`/api/measurements?${query}`, { signal });
}

export function login(username: string, password: string) {
  return request<LoginResponse>("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
}

export function logout(token: string) {
  return request<void>("/api/auth/logout", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function changePassword(
  token: string,
  currentPassword: string,
  newPassword: string,
) {
  return request<void>("/api/auth/password", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ currentPassword, newPassword }),
  });
}

export function saveSeries(token: string, body: SeriesInput, id?: string) {
  return request<Series>(id ? `/api/series/${id}` : "/api/series", {
    method: id ? "PUT" : "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
}

export function deleteSeries(token: string, id: string) {
  return request<void>(`/api/series/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function getSensors(token: string, signal?: AbortSignal) {
  return request<Sensor[]>("/api/sensors", {
    headers: { Authorization: `Bearer ${token}` },
    signal,
  });
}

export function registerSensor(token: string, name: string, seriesId: string) {
  return request<RegisteredSensor>("/api/sensors", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ name, seriesId }),
  });
}

export function unregisterSensor(token: string, id: string) {
  return request<void>(`/api/sensors/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
}
