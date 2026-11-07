import { useState } from "react";
import type { FormEvent } from "react";
import type { Filters, Series } from "../types";

interface Props {
  series: Series[];
  busy: boolean;
  onApply: (filters: Filters) => void;
}

export default function MeasurementFilters({ series, busy, onApply }: Props) {
  const [seriesIds, setSeriesIds] = useState(series.map((item) => item.id));
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [error, setError] = useState("");

  function apply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (from && to && new Date(from) > new Date(to)) {
      setError("The start must be before or equal to the end.");
      return;
    }
    setError("");
    onApply({ seriesIds, from, to });
  }

  function reset() {
    const allIds = series.map((item) => item.id);
    setSeriesIds(allIds);
    setFrom("");
    setTo("");
    setError("");
    onApply({ seriesIds: allIds, from: "", to: "" });
  }

  return (
    <form onSubmit={apply}>
      <fieldset disabled={busy}>
        <legend>Stations / series</legend>
        <div className="series-options">
          {series.map((item) => (
            <label key={item.id}>
              <input
                type="checkbox"
                checked={seriesIds.includes(item.id)}
                onChange={(event) => {
                  setSeriesIds(
                    event.target.checked
                      ? [...seriesIds, item.id]
                      : seriesIds.filter((id) => id !== item.id),
                  );
                }}
              />
              {item.name}
            </label>
          ))}
        </div>
      </fieldset>
      <div className="filter-actions">
        <label>
          From
          <input
            type="datetime-local"
            step="1"
            value={from}
            disabled={busy}
            onChange={(event) => setFrom(event.target.value)}
          />
        </label>
        <label>
          To
          <input
            type="datetime-local"
            step="1"
            value={to}
            disabled={busy}
            onChange={(event) => setTo(event.target.value)}
          />
        </label>
        <button type="submit" disabled={busy}>
          Apply filters
        </button>
        <button type="button" disabled={busy} onClick={reset}>
          Reset
        </button>
      </div>
      {error && (
        <p className="error-text" role="alert">
          {error}
        </p>
      )}
    </form>
  );
}
