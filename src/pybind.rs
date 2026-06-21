use pyo3::prelude::*;
use std::error::Error;
use std::path::PathBuf;

pub fn run() -> Result<(), Box<dyn Error>> {
    Python::attach(|py| -> PyResult<()> {
        let sys = py.import("sys")?;
        let path = sys.getattr("path")?;

        let python_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .to_string_lossy()
            .to_string();

        path.call_method1("insert", (0, python_dir))?;

        let module = PyModule::import(py, "python.mapper")?;
        module.getattr("sync_all_tables")?.call0()?;
        Ok(())
    })?;

    Ok(())
}
