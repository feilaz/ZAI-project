import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { ApiError, getSensors, registerSensor, unregisterSensor } from "../api";
import type { RegisteredSensor, Sensor, Series } from "../types";

interface Props {
  token: string;
  series: Series[];
  onUnauthorized: () => void;
}

export default function SensorManagement({
  token,
  series,
  onUnauthorized,
}: Props) {
  const [sensors, setSensors] = useState<Sensor[]>([]);
  const [created, setCreated] = useState<RegisteredSensor | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [reload, setReload] = useState(0);

  function showError(reason: unknown) {
    if (reason instanceof ApiError && reason.status === 401) onUnauthorized();
    else setError(reason instanceof Error ? reason.message : "Request failed.");
  }

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    getSensors(token, controller.signal)
      .then(setSensors)
      .catch((reason) => {
        if (!controller.signal.aborted) showError(reason);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [token, reload]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const name = String(data.get("name")).trim();
    setError("");
    setMessage("");
    if (!name) {
      setError("Enter a sensor name.");
      return;
    }
    setBusy(true);
    try {
      const sensor = await registerSensor(
        token,
        name,
        String(data.get("seriesId")),
      );
      setCreated(sensor);
      // The list keeps only public sensor fields, never its API key.
      const { apiKey, ...listedSensor } = sensor;
      setSensors((items) => [...items, listedSensor]);
      form.reset();
    } catch (reason) {
      showError(reason);
    } finally {
      setBusy(false);
    }
  }

  async function remove(sensor: Sensor) {
    if (
      !window.confirm(
        `Unregister "${sensor.name}"? Its key will stop working. Existing measurements will remain.`,
      )
    )
      return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await unregisterSensor(token, sensor.id);
      setSensors((items) => items.filter((item) => item.id !== sensor.id));
      if (created?.id === sensor.id) setCreated(null);
      setMessage("Sensor unregistered.");
    } catch (reason) {
      showError(reason);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="sensor-management-title">
      <h2 id="sensor-management-title">Sensors</h2>
      {series.length === 0 ? (
        <p>Create a series before registering a sensor.</p>
      ) : (
        <form onSubmit={submit}>
          <h3>Register sensor</h3>
          <fieldset
            disabled={busy || loading || created !== null}
            className="management-fields"
          >
            <label>
              Name
              <input name="name" required maxLength={100} />
            </label>
            <label>
              Series
              <select name="seriesId" required>
                {series.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
            <button type="submit">Register sensor</button>
          </fieldset>
        </form>
      )}
      {created && (
        <div className="sensor-key" role="status">
          <p>
            Sensor registered. Copy the key now; it cannot be shown again after
            you dismiss this view.
          </p>
          <p>
            Sensor ID: <code>{created.id}</code>
          </p>
          <p>
            Series ID: <code>{created.seriesId}</code>
          </p>
          <label>
            API key
            <input readOnly value={created.apiKey} />
          </label>
          <button onClick={() => setCreated(null)}>Dismiss key</button>
        </div>
      )}
      {(loading || busy) && (
        <p role="status">{loading ? "Loading sensors…" : "Saving…"}</p>
      )}
      {error && (
        <div className="error" role="alert">
          <p>{error}</p>
          <button
            disabled={busy || loading}
            onClick={() => setReload((value) => value + 1)}
          >
            Reload sensors
          </button>
        </div>
      )}
      {message && <p role="status">{message}</p>}
      {!loading &&
        (sensors.length === 0 ? (
          <p>No sensors registered.</p>
        ) : (
          <div
            className="table-scroll"
            tabIndex={0}
            role="region"
            aria-label="Sensor list"
          >
            <table>
              <thead>
                <tr>
                  <th scope="col">Name / ID</th>
                  <th scope="col">Series</th>
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {sensors.map((sensor) => (
                  <tr key={sensor.id}>
                    <th scope="row">
                      {sensor.name}
                      <small className="record-id">{sensor.id}</small>
                    </th>
                    <td>
                      {series.find((item) => item.id === sensor.seriesId)
                        ?.name ?? sensor.seriesId}
                    </td>
                    <td>
                      <button
                        disabled={busy}
                        aria-label={`Unregister sensor ${sensor.name}`}
                        onClick={() => remove(sensor)}
                      >
                        Unregister
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
    </section>
  );
}
