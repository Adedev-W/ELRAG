# rust-me

This repository contains a Rust + Python project with a ScyllaDB backend and document processing helpers. It is a good starting point for building a Retrieval-Augmented Generation (RAG) API.

## What this project includes

- Rust backend scaffold in `src/`
- ScyllaDB support via Docker Compose in `docker-compose.yml`
- Python helpers for Google Cloud Document AI, Vision, and Cloud Storage in `python/lib/`
- Python table model registration and schema sync helpers in `python/models/`
- Documentation about ScyllaDB and schema sync in `docs/`

## RAG API concept

A RAG API typically has three main parts:

1. Document ingestion
2. Retrieval and search over document content or embeddings
3. Prompt generation / answer creation with a language model

This repo provides the foundation for a RAG system:

- ScyllaDB as a storage and retrieval layer
- Python helpers to parse documents and interact with Google Cloud services
- Rust backend readiness for query and API logic

## Prerequisites

- Linux environment
- Docker and Docker Compose
- Rust toolchain
- Python 3.11+ (or compatible environment)
- Google Cloud credentials if you plan to use Document AI / Vision APIs

## Setup

### 1. Start ScyllaDB

From the repo root:

```bash
docker compose up -d
```

This brings up a local ScyllaDB instance on port `9042`.

### 2. Configure environment variables

Set or export these values as needed:

- `SCYLLA_CONTACT_POINT` (default: `127.0.0.1`)
- `SCYLLA_KEYSPACE` (default: `demo`)
- `SCYLLA_URI` (for Rust code, e.g. `127.0.0.1:9042`)

For Google Cloud services, configure the standard service account credentials environment variables such as:

- `GOOGLE_APPLICATION_CREDENTIALS`

### 3. Install Python dependencies

From the repo root:

```bash
python -m pip install -r requirements.txt
```

The Python dependencies include:

- `scylla-driver`
- `google-cloud-documentai`
- `google-cloud-vision`
- `google-cloud-storage`

### 4. Build Rust

From the repo root:

```bash
cargo build
```

## Project structure

- `Cargo.toml` - Rust dependencies and package metadata
- `docker-compose.yml` - local ScyllaDB service definition
- `python/mapper.py` - model registry compatibility exports
- `python/models/base.py` - ScyllaDB connection setup and table sync helper
- `python/models/model.py` - example Cassandra/CQL table models for cloud storage and monitoring data
- `python/lib/documentai.py` - Document AI processing helper
- `python/lib/vision.py` - Vision API helper
- `python/lib/storage_rest.py` - Google Cloud Storage helper
- `docs/` - written notes for ScyllaDB setup and schema sync

## Using the Python model helpers

The Python code in `python/models/` uses Cassandra CQL Engine style models.

- `setup_connection()` initializes a connection to ScyllaDB
- `sync_all_tables()` syncs registered models into the database

Example flow:

```python
from python.models.base import setup_connection, sync_all_tables

setup_connection()
sync_all_tables()
```

## Building a RAG API with this repo

This repository can be used as the starting point for a RAG API by adding the following components:

1. Document ingestion
   - parse files or images with `python/lib/documentai.py` and `python/lib/vision.py`
   - store raw text and metadata in ScyllaDB

2. Embedding generation
   - use an embeddings service or library to convert text into vectors
   - store embeddings in a vector-compatible index or embed them in ScyllaDB rows

3. Retrieval query
   - search documents by text or vector distance
   - retrieve relevant passages from ScyllaDB

4. Response generation
   - use a language model to generate answers from retrieved passages
   - build an API endpoint around the retrieval + generation pipeline

## Recommended next steps

- Add a Rust HTTP server or Python FastAPI service for the RAG API endpoint
- Add document ingestion code to process files and save text/metadata
- Add embedding storage and nearest-neighbor search support
- Connect retrieval results to an LLM prompt generator

## Useful docs in this repo

- `docs/scylla-db.md` - local ScyllaDB development and Rust driver setup
- `docs/scylla-auto-schema-sync.md` - schema sync strategy for ScyllaDB from Rust
- `docs/crud-scylla-beginner.md` - beginner ScyllaDB CRUD patterns in Rust

## Notes

The current `src/main.rs` is a placeholder entrypoint. You can extend it with actual ScyllaDB or HTTP API logic as you build the RAG service.

For an actual RAG implementation, the repository needs:

- document ingestion and preprocessing flows
- embedding creation and vector retrieval
- a query layer that returns relevant documents
- a generation layer that produces final answers
