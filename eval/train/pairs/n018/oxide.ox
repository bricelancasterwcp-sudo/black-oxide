fn main() {
    let v = vec(1, 2, 3, 4)
    let i = len(v) - 1
    while i >= 0 {
        match get(v, i) {
            Some(x) => print(x),
            None => print_str("missing"),
        }
        i = i - 1
    }
}
