fn divide(a: i64, b: i64) -> Result<i64, String> {
    if b == 0 {
        return Err("zero".to_string());
    }
    Ok(a / b)
}

fn main() {
    match divide(20, 4) {
        Ok(n) => println!("{}", n),
        Err(e) => println!("{}", e),
    }
}
