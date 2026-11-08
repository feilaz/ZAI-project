import { useEffect, useState } from "react";
import { getMeasurements, getSeries, MEASUREMENT_LIMIT } from "./api";
import { formatTime, formatValue, groupMeasurements } from "./measurementData";
import type { Filters, Measurement, Series } from "./types";
import AdminAccount from "./components/AdminAccount";
import MeasurementFilters from "./components/MeasurementFilters";
import MeasurementChart from "./components/MeasurementChart";
import MeasurementTable from "./components/MeasurementTable";

export default function App() {
  const [series, setSeries] = useState<Series[]>([]);
  const [filters, setFilters] = useState<Filters | null>(null);
  const [measurements, setMeasurements] = useState<Measurement[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    getSeries(controller.signal)
      .then((items) => {
        setSeries(items);
        setFilters({
          seriesIds: items.map((item) => item.id),
          from: "",
          to: "",
        });
      })
      .catch((reason) => {
        if (!controller.signal.aborted) {
          setError(
            reason instanceof Error ? reason.message : "Cannot load series.",
          );
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!filters) return;
    const controller = new AbortController();
    setSelectedId(null);
    setError("");
    setMeasurements([]);
    if (!filters.seriesIds.length) {
      setLoading(false);
      return;
    }
    setLoading(true);
    getMeasurements(filters, controller.signal)
      .then(setMeasurements)
      .catch((reason) => {
        if (!controller.signal.aborted) {
          setError(
            reason instanceof Error
              ? reason.message
              : "Cannot load measurements.",
          );
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [filters]);

  const visibleSeries = series.filter((item) =>
    filters?.seriesIds.includes(item.id),
  );
  const rows = groupMeasurements(measurements);
  const selected = measurements.find((item) => item.id === selectedId);
  const selectedSeries = series.find((item) => item.id === selected?.seriesId);

  return (
    <main>
      <header>
        <h1>Air quality</h1>
      </header>
      <AdminAccount />

      {series.length > 0 && (
        <MeasurementFilters
          series={series}
          busy={loading}
          onApply={setFilters}
        />
      )}
      {error && (
        <div className="error" role="alert">
          <p>{error}</p>
          <button onClick={() => window.location.reload()}>Retry</button>
        </div>
      )}
      {loading && <p role="status">Loading measurements…</p>}
      {!loading && !error && (
        <>
          {series.length === 0 ? (
            <p>No series available.</p>
          ) : visibleSeries.length === 0 ? (
            <p>Select at least one series.</p>
          ) : measurements.length === 0 ? (
            <p>No measurements match these filters.</p>
          ) : (
            <>
              <p role="status">
                {measurements.length} measurements across {visibleSeries.length}{" "}
                selected series.
              </p>
              {measurements.length === MEASUREMENT_LIMIT && (
                <p>
                  The 10,000-reading limit was reached. Narrow the date range to
                  see a complete result.
                </p>
              )}
              <section aria-labelledby="chart-title">
                <h2 id="chart-title">Measurements over time</h2>
                <MeasurementChart
                  series={visibleSeries}
                  measurements={measurements}
                  selected={selected}
                />
                {selected && (
                  <p role="status">
                    {`${selectedSeries?.name} · ${formatTime(selected.timestamp)} · ${formatValue(selected.value)} ${selectedSeries?.unit || ""}`}
                  </p>
                )}
              </section>
              <section aria-labelledby="table-title">
                <h2 id="table-title">Measurement table</h2>
                <MeasurementTable
                  series={visibleSeries}
                  rows={rows}
                  selectedId={selectedId}
                  onSelect={setSelectedId}
                />
              </section>
            </>
          )}
        </>
      )}
    </main>
  );
}
