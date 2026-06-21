use crate::config::Config;
use crate::error::{AppError, AppResult};
use crate::users::{UsersRepository, UsersStatements};
use scylla::client::session::Session;
use scylla::client::session_builder::SessionBuilder;
use std::sync::Arc;
use tokio::time::timeout;

#[derive(Clone)]
pub struct Engine {
    session: Arc<Session>,
    config: Arc<Config>,
    users_statements: Arc<UsersStatements>,
}

impl Engine {
    pub async fn connect(config: Config) -> AppResult<Self> {
        let session = timeout(
            config.request_timeout,
            SessionBuilder::new().known_node(&config.scylla_uri).build(),
        )
        .await
        .map_err(|_| AppError::timeout("connect", config.request_timeout))?
        .map_err(|err| AppError::database("connect", err))?;

        let session = Arc::new(session);
        let users_statements = Arc::new(UsersStatements::prepare(&session, &config).await?);

        Ok(Self {
            session,
            config: Arc::new(config),
            users_statements,
        })
    }

    pub fn session(&self) -> &Session {
        &self.session
    }

    pub fn config(&self) -> &Config {
        &self.config
    }

    pub fn users(&self) -> UsersRepository {
        UsersRepository::new(
            Arc::clone(&self.session),
            Arc::clone(&self.users_statements),
        )
    }
}
