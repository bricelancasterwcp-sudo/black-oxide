fn main() {
    let v = vec()
    v = push(v, 10)
    v = push(v, 20)
    v = push(v, 30)

    print(unwrap_or(get(v, 1), -1))
    print(unwrap_or(get(v, 5), -1))
}
