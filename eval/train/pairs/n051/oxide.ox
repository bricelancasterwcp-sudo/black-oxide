fn main() {
    let cs = chars("granite")
    match get(cs, 0) {
        Some(a) => print_str(a),
        None => print_str("none"),
    }
    match get(cs, len(cs) - 1) {
        Some(b) => print_str(b),
        None => print_str("none"),
    }
}
