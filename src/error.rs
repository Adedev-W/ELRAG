use std::error::Error;
use std::time::Duration;

pub type BoxError = Box<dyn Error + Send + Sync + 'static>;

#[derive(Debug, thiserror::Error)]
pub enum AppError {
    #[error("operation `{operation}` timed out after {timeout:?}")]
    Timeout {
        operation: &'static str,
        timeout: Duration,
    },
    #[error("database operation `{operation}` failed")]
    Database {
        operation: &'static str,
        #[source]
        source: BoxError,
    },
}

impl AppError {
    pub fn timeout(operation: &'static str, timeout: Duration) -> Self {
        Self::Timeout { operation, timeout }
    }

    pub fn database(operation: &'static str, source: impl Error + Send + Sync + 'static) -> Self {
        Self::Database {
            operation,
            source: Box::new(source),
        }
    }
}

pub type AppResult<T> = Result<T, AppError>;
