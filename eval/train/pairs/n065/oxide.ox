fn main() {
    let v = vec(6, 11, 3, 14, 9)
    print(count_if(v, x -> x > 5))
    print(unwrap_or(max(v), 0))
}
