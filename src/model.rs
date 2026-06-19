// TODO: DataModel belum dipakai oleh server saat ini.
// Pertahankan hanya kalau nanti memang dipakai untuk request/response payload.
pub struct DataModel {
    pub id: i32,
    pub name: String,
    pub email: String,
}

impl DataModel {
    pub fn new(id: i32, name: String, email: String) -> Self {
        Self { id, name, email }
    }
}
