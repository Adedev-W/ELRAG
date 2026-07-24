use api::{
    api_client::ApiClient,
    GetApi
};


pub mod api {
    tonic::include_proto!("api");
}



#[tokio::main]
async fn main()
-> Result<(), Box<dyn std::error::Error>>
{

    let mut client =
        ApiClient::connect(
            "http://127.0.0.1:50051"
        )
        .await?;


    let request =
        tonic::Request::new(
            GetApi {
                name:
                    "Rust".into()
            }
        );


    let response =
        client
        .call_api(request)
        .await?;


    println!(
        "{}",
        response.into_inner().message
    );


    Ok(())
}