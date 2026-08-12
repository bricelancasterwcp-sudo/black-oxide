fn main() {
    match parse_int("417") {
        Some(n) => print(n + 1),
        None => print_str("bad"),
    }
}
