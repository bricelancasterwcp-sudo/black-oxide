fn main() {
    let v = vec()
    v = push(v, 3)
    v = push(v, 8)
    v = push(v, -2)
    v = push(v, 12)
    v = push(v, 7)

    let positive_count = count_if(clone(v), |x| x > 0)
    print(positive_count)
    print(unwrap_or(max(v), 0))
}
