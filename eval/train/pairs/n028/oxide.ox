fn main() {
    match parse_int("abc") {
        Some(n) => print(n),
        None => print_str("bad"),
    }
}
