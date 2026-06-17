mod model;
use std::{
    io::{BufReader, prelude::*},
    net::{TcpListener, TcpStream},
};
use serde_json::json;
fn main() {
    let listener = TcpListener::bind("127.0.0.1:8080").unwrap();
    for stream in listener.incoming() {
        let stream = stream.unwrap();
        handle_connection(stream);
    }
//    let data = DataModel::new(1, "John Doe".into(), "john.doe@example.com".into());
//     println!("Data: {}, {}, {}", data.id, data.name, data.email);
} 


fn handle_connection(mut stream: TcpStream) {
    let buf_reader = BufReader::new(&stream);
    let http_request: Vec<_> = buf_reader
        .lines()
        .map(|result| result.unwrap())
        .take_while(|line| !line.is_empty())
        .collect();
    println!("Request: {http_request:#?}");
    let status_line = "HTTP/1.1 200 OK";
    let json_data = json!({
        "message": "Hello from Rust!",
        "status": "success"
    });
    let contents = json_data.to_string();
    let length = contents.len();

    let response =
        format!("{status_line}\r\nContent-Type: application/json\r\nContent-Length: {length}\r\n\r\n{contents}");

    stream.write_all(response.as_bytes()).unwrap();
}