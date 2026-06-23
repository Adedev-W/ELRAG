use crate::config::Config;
use crate::error::{AppError, AppResult};
use scylla::client::session::Session;
use scylla::statement::prepared::PreparedStatement;
use std::sync::Arc;
use uuid::Uuid;



#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReadMessage {
    pub id: Uuid,
    pub content: String,
    pub user_id: Uuid,
}


pub struct MessagesStatements {
    read: PreparedStatement,

}

impl MessagesStatements {
    pub async fn prepare(session: &Session, config: &Config) -> AppResult<Self> {
        
        let table = messages_table(&config.keyspace);

        let read = session
            .prepare(format!("SELECT id, content, user_id FROM {table}"))
            .await
            .map_err(|err| AppError::database("prepare messages.select_all", err))?;

        Ok(Self {
            read,
        })
    }
    
    
}

fn messages_table(keyspace: &str) -> String {
    format!("{keyspace}.messages")
}

#[derive(Clone)]
pub struct MessagesRepository {
    session: Arc<Session>,
    statements: Arc<MessagesStatements>,
}

impl MessagesRepository {
    pub(crate) fn new(session: Arc<Session>, statements: Arc<MessagesStatements>) -> Self {
        Self {
            session,
            statements,
        }
    }
    pub async fn get_all(&self) -> AppResult<Vec<ReadMessage>> {
        let result = self
            .session
            .execute_unpaged(&self.statements.read, ())
            .await
            .map_err(|err| AppError::database("messages.select_all", err))?;

        let rows = result.into_rows_result()
            .map_err(|err| AppError::database("messages.select_all.rows", err))?;
        let messages = rows
            .rows::<(Uuid, String, Uuid)>()
            .map_err(|err| AppError::database("messages.select_all.decode", err))?
            .map(|row: Result<(Uuid, String, Uuid), scylla::errors::DeserializationError>| {
                let (id, content, user_id) = row
                    .map_err(|err| AppError::database("messages.select_all.row", err))?;
                Ok(ReadMessage { id, content, user_id })
            })
            .collect::<Result<Vec<ReadMessage>, AppError>>()?;


        Ok(messages)
    }
    
}
