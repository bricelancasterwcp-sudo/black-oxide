fn main() {
    match "abc".parse::<i64>() {
        Ok(n) => println!("{}", n),
        Err(_) => println!("bad"),
    }
}
