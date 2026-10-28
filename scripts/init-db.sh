#!/bin/bash
set -e

# Create replication user for streaming replication to db-replica
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
  CREATE ROLE sigpi_replicator WITH REPLICATION PASSWORD 'replicator_password' LOGIN;
EOSQL

# Create readonly user for Superset (connects to db-replica)
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  CREATE USER sigpi_readonly WITH PASSWORD 'readonly_password';
  GRANT CONNECT ON DATABASE sigpi TO sigpi_readonly;
  GRANT USAGE ON SCHEMA public TO sigpi_readonly;
  GRANT SELECT ON ALL TABLES IN SCHEMA public TO sigpi_readonly;
  ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO sigpi_readonly;
EOSQL

# Allow replication connections from any host (required for db-replica)
echo "host replication sigpi_replicator all md5" >> "$PGDATA/pg_hba.conf"

# Reload PostgreSQL configuration to apply pg_hba.conf changes
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" -c "SELECT pg_reload_conf();"
