SELECT pg_advisory_xact_lock(1337);
SET LOCAL TIME ZONE 'UTC';

CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    username TEXT NOT NULL UNIQUE CHECK (length(username) > 0),
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash VARCHAR(64) PRIMARY KEY CHECK (token_hash ~ '^[0-9a-f]{64}$'),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ NOT NULL,
    CHECK (expires_at > created_at)
);

CREATE TABLE IF NOT EXISTS series (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL CHECK (length(name) > 0),
    min_value DOUBLE PRECISION NOT NULL,
    max_value DOUBLE PRECISION NOT NULL,
    color VARCHAR(7) NOT NULL CHECK (color ~ '^#[0-9A-Fa-f]{6}$'),
    icon TEXT,
    unit VARCHAR(20),
    CHECK (min_value < max_value),
    -- Infinity and NaNs can be float value, thus they should be excluded.
    CHECK (min_value > '-Infinity'::DOUBLE PRECISION AND min_value < 'Infinity'::DOUBLE PRECISION),
    CHECK (max_value > '-Infinity'::DOUBLE PRECISION AND max_value < 'Infinity'::DOUBLE PRECISION)
);

CREATE TABLE IF NOT EXISTS sensors (
    id UUID PRIMARY KEY,
    series_id UUID NOT NULL REFERENCES series(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL CHECK (length(name) > 0),
    api_key_hash VARCHAR(64) NOT NULL UNIQUE CHECK (api_key_hash ~ '^[0-9a-f]{64}$'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS measurements (
    id UUID NOT NULL,
    measured_at TIMESTAMPTZ NOT NULL,
    series_id UUID NOT NULL REFERENCES series(id) ON DELETE CASCADE,
    sensor_id UUID REFERENCES sensors(id) ON DELETE SET NULL,
    value DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (id, measured_at),
    CHECK (value > '-Infinity'::DOUBLE PRECISION AND value < 'Infinity'::DOUBLE PRECISION)
);

--  set up the time column as primary key to make TimescaleDB work.
SELECT create_hypertable(
    'measurements',
    by_range('measured_at'),
    create_default_indexes => FALSE,
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS sessions_user_id_idx ON sessions(user_id);
CREATE INDEX IF NOT EXISTS sensors_series_id_idx ON sensors(series_id);
CREATE INDEX IF NOT EXISTS measurements_series_time_idx ON measurements(series_id, measured_at);
CREATE INDEX IF NOT EXISTS measurements_time_idx ON measurements(measured_at);
CREATE INDEX IF NOT EXISTS measurements_sensor_id_idx ON measurements(sensor_id);
