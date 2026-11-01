SELECT current_database(), current_user;

SELECT name, default_version, installed_version
FROM pg_available_extensions
WHERE name = 'timescaledb';
