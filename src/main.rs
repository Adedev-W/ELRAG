mod model;

use serde_json::json;
use std::{
    io::{BufRead, BufReader, Write},
    net::{TcpListener, TcpStream},
};

fn main() {
    let listener = TcpListener::bind("127.0.0.1:8080").unwrap();

    for stream in listener.incoming() {
        match stream {
            Ok(stream) => handle_connection(stream),
            Err(error) => eprintln!("Failed to accept connection: {error}"),
        }
    }
}

fn handle_connection(mut stream: TcpStream) {
    let request_line = {
        let buf_reader = BufReader::new(&stream);
        buf_reader.lines().next().unwrap().unwrap()
    };

    println!("Request: {request_line}");

    let status_line = "HTTP/1.1 200 OK";
    let content_type = "application/json";
    let contents = json!({
        "message": "Hello from Rust!",
        "status": "success"
    })
    .to_string();

    let response = format!(
        "{status_line}\r\nContent-Type: {content_type}\r\nContent-Length: {}\r\n\r\n{contents}",
        contents.len()
    );
    
    stream.write_all(response.as_bytes()).unwrap();
}
