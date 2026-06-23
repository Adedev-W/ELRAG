use crate::config::Config;
use crate::error::{AppError, AppResult};
use scylla::client::session::Session;
use scylla::statement::prepared::PreparedStatement;
use std::sync::Arc;
use uuid::Uuid;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct User {
    pub id: Uuid,
    pub name: String,
    pub email: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CreateUser {
    pub name: String,
    pub email: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UpdateUser {
    pub id: Uuid,
    pub name: String,
    pub email: String,
}

pub struct UsersStatements {
    insert: PreparedStatement,
    select_by_id: PreparedStatement,
    update: PreparedStatement,
    delete: PreparedStatement,
    read: PreparedStatement,
}

impl UsersStatements {
    pub async fn prepare(session: &Session, config: &Config) -> AppResult<Self> {
        let table = users_table(&config.keyspace);

        let read = session
            .prepare(format!("SELECT id, name, email FROM {table}"))
            .await
            .map_err(|err| AppError::database("prepare users.select_all", err))?;

        let insert = session
            .prepare(format!(
                "INSERT INTO {table} (id, name, email) VALUES (?, ?, ?)"
            ))
            .await
            .map_err(|err| AppError::database("prepare users.insert", err))?;

        let select_by_id = session
            .prepare(format!("SELECT id, name, email FROM {table} WHERE id = ?"))
            .await
            .map_err(|err| AppError::database("prepare users.select_by_id", err))?;

        let update = session
            .prepare(format!(
                "UPDATE {table} SET name = ?, email = ? WHERE id = ?"
            ))
            .await
            .map_err(|err| AppError::database("prepare users.update", err))?;

        let delete = session
            .prepare(format!("DELETE FROM {table} WHERE id = ?"))
            .await
            .map_err(|err| AppError::database("prepare users.delete", err))?;

        Ok(Self {
            insert,
            select_by_id,
            update,
            delete,
            read,
        })
    }
}

#[derive(Clone)]
pub struct UsersRepository {
    session: Arc<Session>,
    statements: Arc<UsersStatements>,
}

impl UsersRepository {
    pub(crate) fn new(session: Arc<Session>, statements: Arc<UsersStatements>) -> Self {
        Self {
            session,
            statements,
        }
    }

    pub async fn get_all(&self) -> AppResult<Vec<User>> {
        let result = self
            .session
            .execute_unpaged(&self.statements.read, ())
            .await
            .map_err(|err| AppError::database("users.get_all", err))?;

        let rows = result
            .into_rows_result()
            .map_err(|err| AppError::database("users.get_all.rows", err))?;

        let users = rows
            .rows::<(Uuid, String, String)>()
            .map_err(|err| AppError::database("users.get_all.decode", err))?
            .map(|row: Result<(Uuid, String, String), scylla::errors::DeserializationError>| {
                let (id, name, email) =
                    row.map_err(|err| AppError::database("users.get_all.row", err))?;
                Ok(User { id, name, email })
            })
            .collect::<Result<_, AppError>>()?;
        Ok(users)
    }

    pub async fn create(&self, input: CreateUser) -> AppResult<User> {
        let user = User {
            id: Uuid::new_v4(),
            name: input.name,
            email: input.email,
        };

        self.session
            .execute_unpaged(&self.statements.insert, (user.id, &user.name, &user.email))
            .await
            .map_err(|err| AppError::database("users.create", err))?;

        Ok(user)
    }

    pub async fn get_by_id(&self, id: Uuid) -> AppResult<Option<User>> {
        let result = self
            .session
            .execute_unpaged(&self.statements.select_by_id, (id,))
            .await
            .map_err(|err| AppError::database("users.get_by_id", err))?;

        let rows = result
            .into_rows_result()
            .map_err(|err| AppError::database("users.get_by_id.rows", err))?;

        let mut rows = rows
            .rows::<(Uuid, String, String)>()
            .map_err(|err| AppError::database("users.get_by_id.decode", err))?;

        let Some(row) = rows.next() else {
            return Ok(None);
        };

        let (id, name, email) =
            row.map_err(|err| AppError::database("users.get_by_id.row", err))?;
        Ok(Some(User { id, name, email }))
    }

    pub async fn update(&self, input: UpdateUser) -> AppResult<()> {
        self.session
            .execute_unpaged(
                &self.statements.update,
                (&input.name, &input.email, input.id),
            )
            .await
            .map_err(|err| AppError::database("users.update", err))?;

        Ok(())
    }

    pub async fn delete(&self, id: Uuid) -> AppResult<()> {
        self.session
            .execute_unpaged(&self.statements.delete, (id,))
            .await
            .map_err(|err| AppError::database("users.delete", err))?;

        Ok(())
    }
}

fn users_table(keyspace: &str) -> String {
    format!("{keyspace}.users")
}

#[cfg(test)]
mod tests {
    use super::users_table;

    #[test]
    fn users_table_should_include_keyspace() {
        assert_eq!(users_table("demo"), "demo.users");
    }
}
