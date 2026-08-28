fn main() {
    let v = vec(6, 7, 8, 9)
    match get(v, 0) {
        Some(a) => print(a),
        None => print_str("none"),
    }
    match get(v, len(v) - 1) {
        Some(b) => print(b),
        None => print_str("none"),
    }
}
