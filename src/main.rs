use std::error::Error;

mod pybind;

use rust_me::{Config, Engine};

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    pybind::run()?;

    let engine = Engine::connect(Config::from_env()).await?;
    let users = engine.users();
    let messages = engine.messages();

    // let get_all_users = users.get_all().await?;
    // println!("Users: {:?}", get_all_users);

    let get_all_messages = messages.get_all().await?;
    println!("Messages: {:?}", get_all_messages);

    Ok(())
}
