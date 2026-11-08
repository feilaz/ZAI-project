import { useState } from "react";
import type { FormEvent } from "react";
import { ApiError, deleteSeries, saveSeries } from "../api";
import type { Series } from "../types";

interface Props {
  token: string;
  series: Series[];
  onChange: () => void;
  onUnauthorized: () => void;
}

export default function SeriesManagement({
  token,
  series,
  onChange,
  onUnauthorized,
}: Props) {
  const [editing, setEditing] = useState<Series | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  function showError(reason: unknown) {
    if (reason instanceof ApiError && reason.status === 401) onUnauthorized();
    else setError(reason instanceof Error ? reason.message : "Request failed.");
  }

  function openForm(item: Series | null) {
    setEditing(item);
    setFormOpen(true);
    setError("");
    setMessage("");
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const name = String(data.get("name")).trim();
    const minValue = Number(data.get("minValue"));
    const maxValue = Number(data.get("maxValue"));
    setError("");
    setMessage("");
    if (!name || minValue >= maxValue) {
      setError(
        !name ? "Enter a series name." : "Minimum must be less than maximum.",
      );
      return;
    }
    setBusy(true);
    try {
      await saveSeries(
        token,
        {
          name,
          minValue,
          maxValue,
          color: String(data.get("color")),
          unit: String(data.get("unit")).trim() || null,
          icon: editing?.icon ?? null,
        },
        editing?.id,
      );
      setFormOpen(false);
      setMessage(editing ? "Series updated." : "Series created.");
      onChange();
    } catch (reason) {
      showError(reason);
    } finally {
      setBusy(false);
    }
  }

  async function remove(item: Series) {
    if (
      !window.confirm(
        `Delete "${item.name}" and all its sensors and measurements? This cannot be undone.`,
      )
    )
      return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await deleteSeries(token, item.id);
      if (editing?.id === item.id) setFormOpen(false);
      setMessage("Series deleted.");
      onChange();
    } catch (reason) {
      showError(reason);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="series-management-title">
      <h2 id="series-management-title">Series</h2>
      <button disabled={busy} onClick={() => openForm(null)}>
        New series
      </button>
      {formOpen && (
        <form key={editing?.id ?? "new"} onSubmit={submit}>
          <h3>{editing ? "Edit series" : "New series"}</h3>
          <fieldset disabled={busy} className="management-fields">
            <label>
              Name
              <input
                name="name"
                required
                maxLength={100}
                defaultValue={editing?.name ?? ""}
              />
            </label>
            <label>
              Minimum
              <input
                name="minValue"
                type="number"
                step="any"
                required
                defaultValue={editing?.minValue ?? 0}
              />
            </label>
            <label>
              Maximum
              <input
                name="maxValue"
                type="number"
                step="any"
                required
                defaultValue={editing?.maxValue ?? 500}
              />
            </label>
            <label>
              Color
              <input
                name="color"
                type="color"
                defaultValue={editing?.color ?? "#174f85"}
              />
            </label>
            <label>
              Unit
              <input
                name="unit"
                maxLength={20}
                defaultValue={editing ? (editing.unit ?? "") : "µg/m³"}
              />
            </label>
            <button type="submit">Save series</button>
            <button type="button" onClick={() => setFormOpen(false)}>
              Cancel
            </button>
          </fieldset>
        </form>
      )}
      {busy && <p role="status">Saving…</p>}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {message && <p role="status">{message}</p>}
      {series.length === 0 ? (
        <p>No series available.</p>
      ) : (
        <div
          className="table-scroll"
          tabIndex={0}
          role="region"
          aria-label="Series list"
        >
          <table>
            <thead>
              <tr>
                <th scope="col">Name / ID</th>
                <th scope="col">Range</th>
                <th scope="col">Unit</th>
                <th scope="col">Color</th>
                <th scope="col">Actions</th>
              </tr>
            </thead>
            <tbody>
              {series.map((item) => (
                <tr key={item.id}>
                  <th scope="row">
                    {item.name}
                    <small className="record-id">{item.id}</small>
                  </th>
                  <td>
                    {item.minValue} – {item.maxValue}
                  </td>
                  <td>{item.unit || "—"}</td>
                  <td>{item.color}</td>
                  <td>
                    <button
                      disabled={busy}
                      aria-label={`Edit series ${item.name}`}
                      onClick={() => openForm(item)}
                    >
                      Edit
                    </button>{" "}
                    <button
                      disabled={busy}
                      aria-label={`Delete series ${item.name}`}
                      onClick={() => remove(item)}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
