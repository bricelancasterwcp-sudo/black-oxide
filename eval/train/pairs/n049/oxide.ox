fn main() {
    let v = vec(8, 3, 11, 6)
    let lo = unwrap_or(min(v), 1000000)
    let hi = unwrap_or(max(v), 0)
    print(lo)
    print(hi - lo)
}
