import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatTime, formatValue } from "../measurementData";
import type { Measurement, Series } from "../types";

interface Props {
  series: Series[];
  measurements: Measurement[];
  selected?: Measurement;
}

const linePatterns = ["", "8 4", "2 4", "10 3 2 3"];

export default function MeasurementChart({
  series,
  measurements,
  selected,
}: Props) {
  return (
    <div
      className="chart"
      role="group"
      aria-label="Measurement chart. Values are also available in the table below."
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart accessibilityLayer>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="timestamp"
            type="number"
            scale="time"
            domain={["dataMin", "dataMax"]}
            tickFormatter={(value: number) =>
              new Date(value).toLocaleString("en-GB", {
                day: "2-digit",
                month: "short",
                hour: "2-digit",
                minute: "2-digit",
              })
            }
            minTickGap={40}
          />
          <YAxis />
          <Tooltip
            labelFormatter={(value) => formatTime(Number(value))}
            formatter={(value) =>
              typeof value === "number" ? formatValue(value) : value
            }
          />
          <Legend />
          {series.map((item, index) => (
            <Line
              key={item.id}
              data={measurements
                .filter((measurement) => measurement.seriesId === item.id)
                .map((measurement) => ({
                  timestamp: Date.parse(measurement.timestamp),
                  value: measurement.value,
                }))}
              dataKey="value"
              name={item.name}
              unit={item.unit ? ` ${item.unit}` : ""}
              stroke={item.color}
              strokeDasharray={linePatterns[index % linePatterns.length]}
              isAnimationActive={false}
            />
          ))}
          {selected && (
            <ReferenceDot
              x={Date.parse(selected.timestamp)}
              y={selected.value}
              r={7}
              fill="white"
              stroke="black"
              ifOverflow="extendDomain"
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
