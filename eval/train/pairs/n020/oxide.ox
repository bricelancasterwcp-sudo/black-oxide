fn main() {
    let v = vec(4, 8, 15, 16, 23, 42)
    let total = 0
    for x in v {
        total = total + x
    }
    print(total / len(v))
}
