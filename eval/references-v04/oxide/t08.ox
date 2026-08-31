fn main() {
    let v = vec(3, 8, -2, 12, 7)
    print(count_if(v, |x| x > 0))
    print(unwrap_or(max(v), 0))
}
