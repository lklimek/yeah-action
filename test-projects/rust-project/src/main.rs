use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Debug)]
struct Config {
    name: String,
    version: u32,
}

fn main() {
    let config = Config {
        name: String::from("test"),
        version: 1,
    };
    println!("test rust project: {:?}", config);
}
