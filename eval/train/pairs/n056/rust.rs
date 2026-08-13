fn main() {
    let mut total = 0i64;
    let mut failed = 0;
    for s in ["7", "x", "9", "?"] {
        match s.parse::<i64>() {
            Ok(n) => total += n,
            Err(_) => failed += 1,
        }
    }
    println!("{}", total);
    println!("{}", failed);
}
