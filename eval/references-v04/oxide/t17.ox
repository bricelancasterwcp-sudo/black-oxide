fn main() {
    let v = vec(10, 20, 30)
    print(unwrap_or(get(v, 1), -1))
    print(unwrap_or(get(v, 5), -1))
}
