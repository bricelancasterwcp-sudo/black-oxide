fn main() {
    let v = vec(10, 20)
    match get(v, 1) {
        Some(a) => print(a),
        None => print_str("none"),
    }
    match get(v, 4) {
        Some(b) => print(b),
        None => print_str("none"),
    }
}
