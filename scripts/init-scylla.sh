#!/usr/bin/env bash
set -euo pipefail

keyspace="${SCYLLA_KEYSPACE:-production}"

if [[ ! "${keyspace}" =~ ^[A-Za-z][A-Za-z0-9_]*$ ]]; then
  echo "Invalid SCYLLA_KEYSPACE '${keyspace}'. Use an unquoted CQL identifier: letters, numbers, and underscores; first character must be a letter." >&2
  exit 1
fi
cqlsh scylla 9042 -e "CREATE KEYSPACE IF NOT EXISTS ${keyspace} WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};"
echo "Scylla keyspace '${keyspace}' is ready."
