fn main() {
    let v = vec(1, 2)
    match get(v, 5) {
        Some(x) => print(x),
        None => print_str("none"),
    }
}
