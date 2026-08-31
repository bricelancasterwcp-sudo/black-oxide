fn main() {
    let v = vec()
    for i in range(1, 9) {
        v = push(v, i * 3)
    }
    print(sum(v))
}
