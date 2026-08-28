fn main() {
    for s in ["8", "oak", "15"] {
        match s.parse::<i64>() {
            Ok(n) => println!("{}", n),
            Err(_) => println!("bad"),
        }
    }
}
