use scylla::client::session::Session;
use scylla::client::session_builder::SessionBuilder;
use std::error::Error;
use std::sync::Arc;

#[derive(Clone)]
pub struct Engine {
    session: Arc<Session>,
}

impl Engine {
    pub async fn new() -> Result<Self, Box<dyn Error>> {
        let uri = std::env::var("SCYLLA_URI").unwrap_or_else(|_| "127.0.0.1:9042".to_string());
        let session = SessionBuilder::new().known_node(uri).build().await?;

        Ok(Self {
            session: Arc::new(session),
        })
    }

    pub fn session(&self) -> Arc<Session> {
        Arc::clone(&self.session)
    }

    pub fn session_ref(&self) -> &Session {
        &self.session
    }
}
