import { useEffect, useState } from "react";
import { getMeasurements, getSeries, MEASUREMENT_LIMIT } from "./api";
import { formatTime, formatValue, groupMeasurements } from "./measurementData";
import type { Filters, Measurement, Series } from "./types";
import AdminAccount from "./components/AdminAccount";
import MeasurementFilters from "./components/MeasurementFilters";
import MeasurementChart from "./components/MeasurementChart";
import MeasurementTable from "./components/MeasurementTable";

export default function App() {
  const [reloadSeries, setReloadSeries] = useState(0);
  const [filterVersion, setFilterVersion] = useState(0);
  const [series, setSeries] = useState<Series[]>([]);
  const [filters, setFilters] = useState<Filters | null>(null);
  const [measurements, setMeasurements] = useState<Measurement[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [liveDisconnected, setLiveDisconnected] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    getSeries(controller.signal)
      .then((items) => {
        setSeries(items);
        setFilterVersion((value) => value + 1);
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
  }, [reloadSeries]);

  useEffect(() => {
    if (!filters) return;
    const controller = new AbortController();
    setSelectedId(null);
    setError("");
    setMeasurements([]);
    setLiveDisconnected(false);
    if (!filters.seriesIds.length) {
      setLoading(false);
      return;
    }
    setLoading(true);

    // Coalesce events arriving during a fetch into one follow-up refresh.
    let fetching = false;
    let refreshPending = false;
    async function refresh() {
      refreshPending = true;
      if (fetching) return;
      fetching = true;
      while (refreshPending && !controller.signal.aborted) {
        refreshPending = false;
        try {
          const items = await getMeasurements(filters!, controller.signal);
          if (!controller.signal.aborted) {
            setMeasurements(items);
            setError("");
          }
        } catch (reason) {
          if (!controller.signal.aborted) {
            setError(
              reason instanceof Error
                ? reason.message
                : "Cannot load measurements.",
            );
          }
        } finally {
          if (!controller.signal.aborted) setLoading(false);
        }
      }
      fetching = false;
    }

    const stream = new EventSource("/api/measurements/stream");
    stream.addEventListener("ready", () => {
      setLiveDisconnected(false);
      void refresh();
    });
    stream.addEventListener("measurement", (event) => {
      if (filters.seriesIds.includes(event.data)) void refresh();
    });
    stream.onerror = () => setLiveDisconnected(true);
    void refresh();
    return () => {
      stream.close();
      controller.abort();
    };
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
      <AdminAccount
        series={series}
        onSeriesChange={() => setReloadSeries((value) => value + 1)}
      />

      {series.length > 0 && (
        <MeasurementFilters
          key={filterVersion}
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
      {liveDisconnected && (
        <p className="live-status" role="status">
          Live updates disconnected. Reconnecting…
        </p>
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
