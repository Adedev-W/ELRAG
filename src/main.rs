mod model;
use crate::model::DataModel;
fn main() {

    let data = DataModel::new(1, "John Doe".into(), "john.doe@example.com".into());
    println!("Data: {}, {}, {}", data.id, data.name, data.email);
}
