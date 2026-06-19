# ScyllaDB Lokal + Driver Rust

Dokumen ini menjelaskan cara menyiapkan ScyllaDB lokal untuk development, lalu bagaimana Rust bisa terhubung memakai driver resmi `scylla`.

## Konsep Singkat

ScyllaDB adalah database NoSQL yang kompatibel dengan Cassandra. Driver Rust `scylla` dipakai untuk membuka koneksi CQL, menjalankan query, dan membaca hasil query dari aplikasi Rust.

Di repo ini, server HTTP yang sudah ada belum memakai database. Jadi perubahan ini fokus ke:

- menjalankan ScyllaDB lokal via Docker Compose,
- menambahkan dependency driver Rust versi terbaru,
- menyediakan snippet koneksi yang bisa dipakai saat kamu mau menghubungkan aplikasi ke DB.

## Versi Yang Dipakai

- ScyllaDB image: `scylladb/scylla:2026.1.3`
- Rust driver: `scylla = "1.7.0"`

Versi driver ini mengikuti rilis official terbaru yang didokumentasikan ScyllaDB pada saat penulisan.

## Menjalankan Database

Jalankan ini dari root repo:

```bash
docker compose up -d
```

Yang akan hidup:

- 1 node ScyllaDB lokal
- port CQL `9042` diekspos ke host
- data disimpan di volume Docker bernama `scylla-data`

Untuk melihat status:

```bash
docker compose ps
docker logs -f rust-me-scylla
```

Untuk masuk ke shell CQL:

```bash
docker exec -it rust-me-scylla cqlsh
```

## Kenapa Komposenya Seperti Itu

Konfigurasi compose ini dibuat untuk development lokal, jadi fokusnya adalah sederhana dan stabil:

- `--smp 1` membatasi CPU agar ringan
- `--memory 1G` memberi batas memori dasar
- `--overprovisioned 1` cocok untuk lingkungan lokal/dev
- volume `scylla-data` mencegah data hilang saat container di-restart

Kalau kamu ingin dataset besar atau mendekati produksi, parameter ini bisa dinaikkan nanti.

## Snippet Rust

Tambahkan dependency ini di `Cargo.toml`:

```toml
[dependencies]
scylla = "1.7.0"
tokio = { version = "1", features = ["full"] }
```

Contoh koneksi minimal:

```rust
use scylla::client::session::Session;
use scylla::client::session_builder::SessionBuilder;
use std::error::Error;

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let uri = std::env::var("SCYLLA_URI")
        .unwrap_or_else(|_| "127.0.0.1:9042".to_string());

    let session: Session = SessionBuilder::new()
        .known_node(uri)
        .build()
        .await?;

    session
        .query_unpaged(
            "SELECT cluster_name FROM system.local",
            &[],
        )
        .await?;

    println!("Berhasil connect ke ScyllaDB");
    Ok(())
}
```

## Alur Kerja

1. Jalankan `docker compose up -d`.
2. Tunggu container sehat dan port `9042` siap.
3. Jalankan aplikasi Rust yang memakai `SCYLLA_URI=127.0.0.1:9042`.
4. Buat keyspace dan tabel baru setelah koneksi berhasil.

Contoh CQL:

```sql
CREATE KEYSPACE IF NOT EXISTS demo
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

CREATE TABLE IF NOT EXISTS demo.users (
    id int PRIMARY KEY,
    name text,
    email text
);
```

## Catatan Penting

- File `src/main.rs` saat ini masih server HTTP sederhana dan belum memakai DB.
- Dokumen ini sengaja dibuat sebagai jembatan supaya kamu bisa lanjut menghubungkan handler HTTP ke query ScyllaDB tanpa mengubah semua struktur sekaligus.
- Kalau kamu mau, langkah berikutnya adalah membuat endpoint yang benar-benar membaca/menulis data ke tabel `demo.users`.
