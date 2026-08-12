fn main() {
    match "417".parse::<i64>() {
        Ok(n) => println!("{}", n + 1),
        Err(_) => println!("bad"),
    }
}
