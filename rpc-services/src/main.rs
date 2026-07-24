use tonic::{
    transport::Server,
    Request,
    Response,
    Status
};


pub mod api {
    tonic::include_proto!("api");
}


use api::{
    api_server::{
        Api,
        ApiServer
    },
    GetApi,
    OutApi
};


#[derive(Default)]
struct MyApi;


#[tonic::async_trait]
impl Api for MyApi {

    async fn call_api(
        &self,
        request: Request<GetApi>
    )
    -> Result<Response<OutApi>, Status>
    {

        let name = request
            .into_inner()
            .name;


        let reply = OutApi {
            message:
                format!("Halo {}", name)
        };


        Ok(Response::new(reply))
    }
}



#[tokio::main]
async fn main()
-> Result<(), Box<dyn std::error::Error>>
{

    let addr =
        "127.0.0.1:50051"
        .parse()?;


    let api =
        MyApi::default();


    println!("Server running");


    Server::builder()
        .add_service(
            ApiServer::new(api)
        )
        .serve(addr)
        .await?;


    Ok(())
}