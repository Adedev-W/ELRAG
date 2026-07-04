# Auto Sync Schema ScyllaDB dari Rust

Dokumen ini menjelaskan cara membuat aplikasi Rust yang bisa menyelaraskan schema ScyllaDB secara otomatis saat startup.

Tujuannya sederhana:

- kamu definisikan model dan metadata kolom di Rust,
- aplikasi membandingkan metadata itu dengan schema database,
- kalau ada kolom baru, aplikasi menjalankan `ALTER TABLE ... ADD`,
- kamu tidak perlu masuk ke `cqlsh` untuk menambah kolom manual.

## Kenapa Pendekatan Ini Dipakai

ScyllaDB tidak punya konsep ORM migration otomatis seperti beberapa database SQL. Karena itu, pendekatan yang aman dan realistis adalah:

1. pastikan keyspace ada,
2. pastikan tabel ada,
3. baca daftar kolom yang sudah ada,
4. tambahkan kolom baru yang belum ada,
5. jangan ubah atau hapus kolom otomatis.

Pendekatan ini aman untuk development dan bootstrap aplikasi, karena hanya melakukan perubahan yang bersifat additive.

## Batasan Penting

- otomatis menambah kolom baru: `ALTER TABLE ... ADD`
- otomatis membuat keyspace jika belum ada
- otomatis membuat tabel jika belum ada
- tidak otomatis rename kolom
- tidak otomatis drop kolom
- tidak otomatis mengubah tipe kolom existing

Kalau kamu butuh migration yang destruktif, itu sebaiknya dibuat manual dan terkontrol.

## Struktur Kode

Implementasi di repo ini memakai tiga bagian:

- `src/users.rs`
  - model Rust dan metadata kolom
- `src/schema.rs`
  - logic sync schema ke ScyllaDB
- `src/engine.rs`
  - koneksi ke ScyllaDB dan entry point bootstrap schema

## Alur Kerja

Urutannya seperti ini:

1. aplikasi start
2. `Engine::new()` membuat session ke ScyllaDB
3. `engine.sync_schema()` dipanggil
4. aplikasi mengecek keyspace dan tabel `production.users`
5. aplikasi baca kolom yang sudah ada dari `system_schema.columns`
6. kalau ada kolom di model Rust tetapi belum ada di database, aplikasi menjalankan `ALTER TABLE`
7. setelah schema cocok, aplikasi lanjut menjalankan logic bisnis

## Contoh Model Rust

```rust
use uuid::Uuid;

#[derive(Debug, Clone)]
pub struct UserModel {
    pub id: Uuid,
    pub name: String,
    pub email: String,
    pub created_at: Option<i64>,
}
```

Model di atas adalah representasi data di code. Karena Rust tidak punya reflection runtime yang sederhana untuk membaca field struct secara otomatis, kita tambahkan metadata kolom secara eksplisit:

```rust
impl UserModel {
    pub const fn columns() -> &'static [ColumnDef] {
        &[
            ColumnDef { name: "id", cql_type: "uuid" },
            ColumnDef { name: "name", cql_type: "text" },
            ColumnDef { name: "email", cql_type: "text" },
            ColumnDef { name: "created_at", cql_type: "timestamp" },
        ]
    }
}
```

Poin penting:

- struct dipakai untuk mewakili data aplikasi
- `columns()` dipakai sebagai source of truth schema
- kalau kamu menambah field baru, tambahkan juga metadata kolomnya

## Code Sync Schema

Logika sync ada di `src/schema.rs`.

### 1. Buat keyspace

```rust
CREATE KEYSPACE IF NOT EXISTS production
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1}
```

Ini aman dijalankan berulang.

### 2. Buat tabel jika belum ada

```rust
CREATE TABLE IF NOT EXISTS production.users (
    id uuid PRIMARY KEY,
    name text,
    email text,
    created_at timestamp
)
```

Ini memastikan bootstrap awal jalan walaupun database masih kosong.

### 3. Baca kolom existing

Aplikasi membaca `system_schema.columns` untuk mendapatkan daftar kolom yang sudah ada di table.

### 4. Tambahkan kolom yang belum ada

Kalau model Rust punya kolom baru, aplikasi menjalankan query seperti:

```rust
ALTER TABLE production.users ADD phone text
```

Pola ini adalah inti dari auto-sync yang aman.

## Contoh Implementasi

### `src/engine.rs`

```rust
impl Engine {
    pub async fn sync_schema(&self) -> Result<(), Box<dyn Error>> {
        schema::sync(self.session_ref()).await
    }
}
```

### `src/main.rs`

```rust
#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let engine = Engine::new().await?;
    engine.sync_schema().await?;

    let session = engine.session_ref();
    create_user(session, Uuid::new_v4(), "John Doe", "john.doe@example.com").await?;

    Ok(())
}
```

Urutan ini penting:

- koneksi dulu
- sync schema dulu
- baru jalankan query bisnis

## Cara Menambah Kolom Baru

Misalnya kamu ingin menambah field `phone`.

### Langkah 1

Tambahkan field ke model Rust:

```rust
pub struct UserModel {
    pub id: Uuid,
    pub name: String,
    pub email: String,
    pub phone: Option<String>,
    pub created_at: Option<i64>,
}
```

### Langkah 2

Tambahkan metadata kolom:

```rust
ColumnDef {
    name: "phone",
    cql_type: "text",
}
```

### Langkah 3

Jalankan aplikasi lagi.

### Langkah 4

Saat startup, aplikasi akan mendeteksi kolom `phone` belum ada, lalu menjalankan:

```sql
ALTER TABLE production.users ADD phone text;
```

### Langkah 5

Verifikasi dengan query CQL atau lewat code bahwa kolom sudah tersedia.

## Kenapa Tidak Drop atau Rename Otomatis

Karena operasi itu berisiko:

- data bisa hilang,
- query lama bisa rusak,
- bentuk data existing bisa tidak cocok lagi.

Untuk sistem nyata, additive migration jauh lebih aman dibanding schema rewrite otomatis.

## Contoh Alur Debugging

Kalau sync gagal, cek urutan ini:

1. pastikan container ScyllaDB hidup
2. pastikan `SCYLLA_URI` benar
3. pastikan keyspace `production` bisa dibuat
4. pastikan table `production.users` bisa dibuat
5. pastikan query ke `system_schema.columns` sukses
6. pastikan tipe kolom valid di ScyllaDB

## Ringkasan Praktis

Kalau kamu ingin workflow yang tidak ribet:

- definisikan model dan metadata kolom di Rust
- panggil `engine.sync_schema()` saat startup
- biarkan aplikasi menambah kolom baru secara otomatis
- hindari perubahan destruktif otomatis

Dokumen pendukung:

- [ScyllaDB Lokal + Driver Rust](/docs/scylla-db)
- [CRUD ScyllaDB untuk Pemula](/docs/crud-scylla-beginner)
