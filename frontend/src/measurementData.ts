import type { Measurement } from "./types";

export interface MeasurementRow {
  timestamp: number;
  readings: Record<string, Measurement[]>;
}

export function groupMeasurements(
  measurements: Measurement[],
): MeasurementRow[] {
  const rows = new Map<number, MeasurementRow>();
  for (const measurement of measurements) {
    const timestamp = Date.parse(measurement.timestamp);
    let row = rows.get(timestamp);
    if (!row) {
      row = { timestamp, readings: {} };
      rows.set(timestamp, row);
    }
    // Keep every reading, even if a series has two readings at the same instant.
    (row.readings[measurement.seriesId] ??= []).push(measurement);
  }
  return [...rows.values()].sort((a, b) => a.timestamp - b.timestamp);
}

export function formatTime(timestamp: number | string): string {
  return new Date(timestamp).toLocaleString("en-GB");
}

export function formatValue(value: number): string {
  return value.toLocaleString("en-GB", { maximumFractionDigits: 2 });
}
