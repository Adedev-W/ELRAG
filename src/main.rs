use rust_me::Engine;
use std::error::Error;

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let engine = Engine::new().await?;
    let session = engine.session();

    session
        .query_unpaged("SELECT cluster_name FROM system.local", &[])
        .await?;
    println!("Connected to ScyllaDB!");

    let qry = session.get_cluster_state();
    let nodes = qry.get_nodes_info();

    for node in nodes {
        println!("Node ID: {}", node.host_id);
        println!("Address: {:?}", node.address);
        println!("Datacenter: {:?}", node.datacenter);
        println!("Rack: {:?}", node.rack);
    }
    get_users(session.as_ref()).await?;
    Ok(())
}

async fn get_users(session: &Session) -> Result<(), Box<dyn Error>> {
    let query = "SELECT id, name, email FROM users";
    let rows = session.query_unpaged(query, &[]).await?.into_rows_result()?;

    for row in rows.rows::<(String, )>()? {
        let (cluster_name) = row?;
        println!("Cluster Name: {:?}", cluster_name);
    }


    Ok(())
}
