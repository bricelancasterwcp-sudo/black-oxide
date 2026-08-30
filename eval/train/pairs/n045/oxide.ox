fn main() {
    let v = vec(6, 7, 8, 9)
    print(unwrap_or(get(v, 0), 0))
    print(unwrap_or(get(v, len(v) - 1), 0))
}
