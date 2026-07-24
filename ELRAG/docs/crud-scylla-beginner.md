# CRUD ScyllaDB untuk Pemula

Dokumen ini menjelaskan cara membuat CRUD sederhana ke ScyllaDB dengan Rust. Fokusnya bukan hanya contoh kode, tetapi juga konsep di balik kode: apa yang dilakukan, kenapa dipakai, dan apa yang sebaiknya dihindari.

Target pembaca:

- pemula yang baru belajar Rust backend,
- orang yang baru pertama kali memakai ScyllaDB,
- pembaca yang ingin memahami pola reusable session sebelum masuk ke handler HTTP.

## Gambaran Besar

CRUD berarti:

- `Create`: menambah data baru
- `Read`: membaca data
- `Update`: mengubah data
- `Delete`: menghapus data

Di ScyllaDB, kita biasanya bekerja dengan:

- `Session`: koneksi reusable ke database
- `Query`: perintah CQL untuk membaca/menulis data
- `Binding parameter`: cara mengirim data ke query tanpa menyusun string manual
- `Table schema`: struktur tabel tempat data disimpan

Pola yang dipakai di repo ini adalah:

- session dibuild sekali saat startup,
- session disimpan di `Engine`,
- handler atau service lain cukup clone handle session,
- hindari `SessionBuilder::build().await` di dalam request path.

## Konsep Dasar

### 1. Database

Database adalah tempat menyimpan data agar bisa dipakai lagi nanti.

Dalam contoh ini kita pakai ScyllaDB, yaitu database NoSQL yang kompatibel dengan Cassandra.

Kenapa ini penting:

- data tidak hilang saat aplikasi berhenti,
- data bisa dibaca dan diubah oleh banyak request,
- query bisa dioptimalkan sesuai pola akses yang kita butuhkan.

### 2. Session

`Session` adalah objek koneksi utama ke ScyllaDB.

Kenapa tidak membuat session setiap request:

- membangun koneksi itu mahal,
- request jadi lebih lambat,
- sistem jadi boros resource,
- berisiko bikin connection storm saat traffic naik.

Best practice:

- build satu kali saat startup,
- share session ke semua handler,
- clone handle, bukan bangun ulang koneksi.

Bad practice:

- memanggil `SessionBuilder::build().await` di setiap endpoint,
- menyimpan string koneksi lalu membuat koneksi baru setiap query,
- membuka koneksi dari dalam loop request tanpa pooling/reuse.

### 3. CQL

CQL adalah bahasa query yang dipakai ScyllaDB.

Mirip SQL, tetapi ada beberapa perbedaan desain:

- data model disesuaikan untuk akses yang cepat dan terdistribusi,
- struktur tabel harus dirancang mengikuti pola query,
- primary key sangat penting.

### 4. Primary Key

Primary key adalah identitas unik data.

Contoh:

- `id` dipakai untuk membedakan satu user dari user lain.

Kenapa penting:

- ScyllaDB memakai primary key untuk distribusi data,
- operasi `read`, `update`, dan `delete` biasanya paling aman dan cepat jika memakai primary key.

Bad practice:

- membuat tabel lalu berharap semua query ad hoc akan cepat,
- memakai query tanpa memahami primary key,
- menaruh data yang sering dicari tetapi tidak masuk desain primary key.

## Skema Contoh

Kita pakai tabel `users` sebagai contoh sederhana.

```sql
CREATE KEYSPACE IF NOT EXISTS demo
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

CREATE TABLE IF NOT EXISTS demo.users (
    id uuid PRIMARY KEY,
    name text,
    email text,
    created_at timestamp
);
```

### Penjelasan Syntax

- `CREATE KEYSPACE IF NOT EXISTS`
  - apa: membuat namespace database jika belum ada
  - kenapa: aman dijalankan berulang saat development
  - bagaimana: cocok dipakai saat bootstrap awal

- `WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1}`
  - apa: aturan replikasi data
  - kenapa: untuk local dev kita cukup 1 replika
  - bagaimana: di production nilainya biasanya lebih kompleks

- `CREATE TABLE IF NOT EXISTS`
  - apa: membuat tabel jika belum ada
  - kenapa: mencegah error saat startup diulang
  - bagaimana: berguna untuk bootstrap schema

- `id uuid PRIMARY KEY`
  - apa: kolom identitas unik
  - kenapa: jadi kunci utama untuk operasi CRUD
  - bagaimana: gunakan UUID supaya mudah dibuat dari aplikasi

- `name text`, `email text`, `created_at timestamp`
  - apa: kolom data user
  - kenapa: menyimpan atribut dasar yang dibutuhkan aplikasi
  - bagaimana: tipe data dipilih sesuai isi kolom

### Catatan Sync Schema

Untuk workflow yang lebih enak, schema tidak perlu dibuat manual di `cqlsh` setiap kali ada perubahan kecil.

Di repo ini, pendekatan yang disarankan adalah:

- definisikan model dan metadata kolom di Rust,
- panggil `engine.sync_schema()` saat startup,
- biarkan aplikasi membuat `CREATE TABLE IF NOT EXISTS` dan `ALTER TABLE ... ADD` otomatis.

Panduan langkah demi langkah ada di [Auto Sync Schema ScyllaDB dari Rust](/docs/scylla-auto-schema-sync).

## Setup Rust

Dependency yang dipakai di repo ini:

```toml
[dependencies]
scylla = "1.7.0"
tokio = { version = "1", features = ["full"] }
uuid = { version = "1", features = ["v4"] }
```

### Penjelasan Syntax

- `scylla = "1.7.0"`
  - apa: driver Rust untuk ScyllaDB
  - kenapa: dipakai untuk membuka session dan menjalankan query
  - bagaimana: gunakan versi yang kompatibel dengan codebase

- `tokio = { version = "1", features = ["full"] }`
  - apa: async runtime
  - kenapa: operasi database di sini bersifat async
  - bagaimana: diperlukan agar `await` bisa dipakai

## Engine Reusable

Di repo ini, session dibungkus dalam `Engine`.

```rust
use scylla::client::session::Session;
use scylla::client::session_builder::SessionBuilder;
use std::error::Error;
use std::sync::Arc;

#[derive(Clone)]
pub struct Engine {
    session: Arc<Session>,
}
```

### Penjelasan Syntax

- `use ...`
  - apa: mengambil tipe dari crate lain
  - kenapa: supaya kode bisa memakai `Session`, `SessionBuilder`, `Arc`
  - bagaimana: Rust mewajibkan import tipe yang dipakai

- `Arc<Session>`
  - apa: reference-counted shared ownership
  - kenapa: session bisa dibagikan ke banyak handler tanpa memindahkan ownership
  - bagaimana: `Arc::clone()` hanya menambah counter, bukan membuat koneksi baru

- `#[derive(Clone)]`
  - apa: meminta Rust membuat implementasi `Clone`
  - kenapa: `Engine` mudah dipindah/di-share antar layer
  - bagaimana: penting untuk state aplikasi yang dipakai di banyak handler

### Kenapa Ini Best Practice

- session dibuat sekali saat startup,
- handler hanya clone handle,
- lifetime lebih mudah dikelola,
- performa lebih stabil.

### Bad Practice

- membuat `Engine` atau `Session` baru di setiap request,
- menaruh logic koneksi langsung di handler,
- membiarkan query logic menyebar tanpa wrapper.

## Create

Contoh insert user:

```rust
use scylla::client::session::Session;
use std::error::Error;
use uuid::Uuid;

pub async fn create_user(
    session: &Session,
    id: Uuid,
    name: &str,
    email: &str,
) -> Result<(), Box<dyn Error>> {
    let query = "INSERT INTO demo.users (id, name, email, created_at) VALUES (?, ?, ?, toTimestamp(now()))";

    session
        .query_unpaged(query, (id, name, email))
        .await?;

    Ok(())
}
```

### Penjelasan Syntax

- `pub async fn create_user`
  - apa: fungsi async yang bisa dipanggil dari modul lain
  - kenapa: query database menunggu I/O
  - bagaimana: `async` wajib agar bisa memakai `.await`

- `session: &Session`
  - apa: referensi ke session
  - kenapa: tidak perlu ownership penuh
  - bagaimana: cocok untuk share session hasil startup

- `id: Uuid`, `name: &str`, `email: &str`
  - apa: input data user
  - kenapa: tipe eksplisit membuat API jelas
  - bagaimana: `Uuid` baik untuk identitas unik

- `INSERT INTO demo.users ... VALUES (?, ?, ?, toTimestamp(now()))`
  - apa: query insert
  - kenapa: menyimpan baris baru
  - bagaimana: pakai parameter binding `?` supaya aman

- `.query_unpaged(query, (id, name, email))`
  - apa: menjalankan query dengan parameter
  - kenapa: menghindari SQL/CQL injection dan string concatenation
  - bagaimana: tuple dipakai untuk mengisi placeholder sesuai urutan

- `await?`
  - apa: menunggu hasil async dan meneruskan error jika ada
  - kenapa: query bisa gagal
  - bagaimana: pattern idiomatik Rust untuk error propagation

### Best Practice Create

- gunakan parameter binding,
- validasi input sebelum query,
- gunakan UUID atau primary key yang jelas,
- simpan `created_at` di sisi database atau application layer secara konsisten.

### Bad Practice Create

- `format!("INSERT ... {}", user_input)`,
- menerima input mentah lalu langsung dijadikan query,
- tidak memeriksa duplikasi primary key,
- membuat session baru hanya untuk insert.

## Read

Contoh membaca user berdasarkan `id`:

```rust
use scylla::client::session::Session;
use std::error::Error;
use uuid::Uuid;

pub async fn get_user_by_id(
    session: &Session,
    id: Uuid,
) -> Result<Option<(Uuid, String, String)>, Box<dyn Error>> {
    let query = "SELECT id, name, email FROM demo.users WHERE id = ?";

    let result = session.query_unpaged(query, (id,)).await?;
    let rows = result.into_rows_result()?;

    let mut iter = rows.rows::<(Uuid, String, String)>()?;
    if let Some(row) = iter.next() {
        Ok(Some(row?))
    } else {
        Ok(None)
    }
}
```

### Penjelasan Syntax

- `Result<Option<...>, Box<dyn Error>>`
  - apa: hasil bisa sukses, error, atau tidak ada data
  - kenapa: read by id bisa tidak menemukan baris
  - bagaimana: `Option` dipakai untuk membedakan “tidak ada data” dari error

- `WHERE id = ?`
  - apa: filter berdasarkan primary key
  - kenapa: ini cara paling umum dan efisien
  - bagaimana: cocok untuk lookup langsung

- `rows::<T>()?` lalu `next()`
  - apa: membaca row secara iterator
  - kenapa: aman dipakai untuk mengambil hasil pertama jika ada
  - bagaimana: cocok untuk query yang hasilnya satu baris atau tidak ada

### Best Practice Read

- baca dengan primary key jika memungkinkan,
- pilih kolom yang memang dibutuhkan,
- tangani kasus data tidak ditemukan,
- gunakan tipe hasil yang jelas.

### Bad Practice Read

- `SELECT *` tanpa alasan,
- membaca tabel besar tanpa filter,
- menganggap hasil pasti ada,
- mendesain tabel hanya untuk query yang belum didefinisikan.

## Update

Contoh update nama dan email user:

```rust
use scylla::client::session::Session;
use std::error::Error;
use uuid::Uuid;

pub async fn update_user(
    session: &Session,
    id: Uuid,
    name: &str,
    email: &str,
) -> Result<(), Box<dyn Error>> {
    let query = "UPDATE demo.users SET name = ?, email = ? WHERE id = ?";

    session
        .query_unpaged(query, (name, email, id))
        .await?;

    Ok(())
}
```

### Penjelasan Syntax

- `UPDATE demo.users SET ... WHERE id = ?`
  - apa: mengubah data pada baris tertentu
  - kenapa: update harus jelas targetnya
  - bagaimana: primary key dipakai supaya baris yang diubah spesifik

- `(name, email, id)`
  - apa: urutan parameter untuk placeholder
  - kenapa: placeholder diisi sesuai urutan query
  - bagaimana: urutan yang salah akan menghasilkan data salah

### Best Practice Update

- pastikan target row jelas,
- ubah hanya field yang perlu,
- validasi data sebelum update,
- pertimbangkan apakah sebagian field boleh nullable.

### Bad Practice Update

- update tanpa `WHERE`,
- update dengan target yang tidak jelas,
- menulis ulang semua kolom padahal hanya satu yang berubah,
- menyusun query manual dari input user.

## Delete

Contoh hapus user:

```rust
use scylla::client::session::Session;
use std::error::Error;
use uuid::Uuid;

pub async fn delete_user(
    session: &Session,
    id: Uuid,
) -> Result<(), Box<dyn Error>> {
    let query = "DELETE FROM demo.users WHERE id = ?";

    session.query_unpaged(query, (id,)).await?;

    Ok(())
}
```

### Penjelasan Syntax

- `DELETE FROM demo.users WHERE id = ?`
  - apa: menghapus baris tertentu
  - kenapa: delete tanpa target berbahaya
  - bagaimana: selalu pakai primary key atau kondisi yang memang aman

### Best Practice Delete

- gunakan primary key,
- cek dulu data memang ada kalau user experience membutuhkannya,
- pertimbangkan soft delete jika data harus bisa dipulihkan.

### Bad Practice Delete

- delete tanpa filter,
- langsung hapus data penting tanpa audit,
- menyembunyikan delete berbahaya di balik query otomatis.

## Cara Memakai Dari File Lain

Karena `Engine` diekspor dari `src/lib.rs`, file lain cukup import:

```rust
use rust_me::Engine;
```

Contoh pola pemakaian:

```rust
pub async fn handler(engine: Engine) -> Result<(), Box<dyn std::error::Error>> {
    let session = engine.session();
    let _ = session.query_unpaged("SELECT cluster_name FROM system.local", &[]).await?;
    Ok(())
}
```

### Penjelasan Syntax

- `engine.session()`
  - apa: mengambil clone handle session
  - kenapa: satu session dipakai bersama
  - bagaimana: aman dipakai di banyak handler

- `let _ = ...`
  - apa: mengabaikan nilai hasil
  - kenapa: kadang dipakai saat hanya butuh efek query
  - bagaimana: jangan dipakai kalau hasilnya sebenarnya penting

## Best Practice vs Bad Practice

### Best Practice

- build session sekali saat startup,
- share session dengan `Arc`,
- gunakan parameter binding,
- pilih primary key yang sesuai pola akses,
- tangani error dengan `Result`,
- tangani data kosong dengan `Option`,
- tulis query minimal yang memang dibutuhkan.

### Bad Practice

- build koneksi per request,
- concat string query dari input user,
- memakai `SELECT *` tanpa kebutuhan,
- mengabaikan hasil error,
- menyimpan logika database langsung di banyak handler tanpa layer yang jelas,
- update/delete tanpa `WHERE`.

## Alur Implementasi Sederhana

1. Buat keyspace dan tabel.
2. Build `Engine` sekali saat startup.
3. Share `Engine` ke handler atau service lain.
4. Buat fungsi `create_user`, `get_user_by_id`, `update_user`, `delete_user`.
5. Panggil fungsi itu dari endpoint HTTP atau command line.

## Contoh Struktur File

Contoh susunan yang enak untuk belajar:

```text
src/
  lib.rs
  engine.rs
  users.rs
  main.rs
docs/
  crud-scylla-beginner.md
```

Rekomendasi isi:

- `engine.rs`: inisialisasi session reusable
- `users.rs`: fungsi CRUD untuk tabel `users`
- `main.rs`: startup aplikasi

## Ringkasan

Kalau kamu baru belajar, ingat 3 hal ini:

- session dibangun sekali, jangan berulang-ulang,
- query harus memakai parameter, jangan string manual,
- CRUD yang bagus selalu mengikuti desain tabel dan primary key.

Kalau konsep ini sudah paham, langkah berikutnya adalah memindahkan fungsi CRUD ke modul khusus lalu memanggilnya dari handler HTTP.
