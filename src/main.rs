use std::error::Error;

mod pybind;

fn main() -> Result<(), Box<dyn Error>> {
    pybind::run()
}
