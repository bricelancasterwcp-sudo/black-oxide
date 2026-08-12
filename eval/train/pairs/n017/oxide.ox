fn main() {
    let v = vec(10, 20, 30, 40)
    match get(v, 2) {
        Some(x) => print(x),
        None => print_str("missing"),
    }
}
