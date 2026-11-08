export interface Series {
  id: string;
  name: string;
  minValue: number;
  maxValue: number;
  color: string;
  icon?: string | null;
  unit?: string | null;
}

export interface Measurement {
  id: string;
  seriesId: string;
  sensorId?: string;
  value: number;
  timestamp: string;
}

export interface Filters {
  seriesIds: string[];
  from: string;
  to: string;
}

export interface LoginResponse {
  accessToken: string;
  expiresIn: number;
}

export type SeriesInput = Omit<Series, "id">;

export interface Sensor {
  id: string;
  name: string;
  seriesId: string;
  createdAt: string;
}

export interface RegisteredSensor extends Sensor {
  apiKey: string;
}
