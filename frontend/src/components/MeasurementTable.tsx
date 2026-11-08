import { Fragment } from "react";
import { formatTime, formatValue } from "../measurementData";
import type { MeasurementRow } from "../measurementData";
import type { Series } from "../types";

interface Props {
  series: Series[];
  rows: MeasurementRow[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export default function MeasurementTable({
  series,
  rows,
  selectedId,
  onSelect,
}: Props) {
  return (
    <div
      className="table-scroll"
      tabIndex={0}
      role="region"
      aria-label="Scrollable measurement table"
    >
      <table>
        <thead>
          <tr>
            <th scope="col">Time</th>
            {series.map((item) => (
              <th scope="col" key={item.id}>
                {item.name}
                {item.unit && <span className="column-unit">{item.unit}</span>}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.timestamp}>
              <th scope="row">
                <time dateTime={new Date(row.timestamp).toISOString()}>
                  {formatTime(row.timestamp)}
                </time>
              </th>
              {series.map((item) => (
                <td key={item.id}>
                  {row.readings[item.id]?.map((measurement) => (
                    <Fragment key={measurement.id}>
                      <button
                        className="reading"
                        aria-pressed={selectedId === measurement.id}
                        aria-label={`${item.name}, ${formatTime(row.timestamp)}, ${formatValue(measurement.value)} ${item.unit || ""}`}
                        onClick={() => onSelect(measurement.id)}
                      >
                        {formatValue(measurement.value)}
                      </button>
                      <span className="print-only">
                        {formatValue(measurement.value)}{" "}
                      </span>
                    </Fragment>
                  )) ?? "—"}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
