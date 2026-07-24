# ELRAG

Core project untuk ELRAG. Folder ini berisi API Python, service layer, database models, MCP integration, dokumentasi ScyllaDB, dan Rust RPC services untuk microservices.

## Structure

- `python/elrag/` - package Python core untuk FastAPI, service backend, models, library wrapper, dan MCP tools.
- `rpc-services/` - Rust tonic/prost RPC service dan protobuf definitions.
- `docs/` - dokumentasi ScyllaDB dan schema sync.
- `docker-compose.yml` - ScyllaDB lokal.
- `requirements.txt` - dependency Python core.
- `tests/` - test untuk core Python.

## Development

Install dependency Python:

```bash
python -m pip install -r ELRAG/requirements.txt
```

Jalankan ScyllaDB lokal:

```bash
cd ELRAG
docker compose up -d
```

Jalankan API lokal:

```bash
PYTHONPATH=ELRAG/python python -m uvicorn elrag.main:app --reload --port 8080
```

Build Rust RPC service:

```bash
cd ELRAG/rpc-services
cargo build
```

## Configuration

- `SCYLLA_CONTACT_POINT` default: `127.0.0.1`
- `SCYLLA_KEYSPACE` default: `production`
- Google Cloud helpers memakai credential standar seperti `GOOGLE_APPLICATION_CREDENTIALS`.
