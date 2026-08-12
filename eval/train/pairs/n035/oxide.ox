fn divide(a: Int, b: Int) -> Result<Int, Str> {
    if b == 0 {
        return Err("zero")
    }
    Ok(a / b)
}

fn main() {
    match divide(20, 4) {
        Ok(n) => print(n),
        Err(e) => print_str(e),
    }
}
