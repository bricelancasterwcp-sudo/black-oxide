fn main() {
    let v = vec()
    for i in range(1, 7) {
        v = push(v, i * 4)
    }
    let total = 0
    for x in v {
        total = total + x
    }
    print(total)
}
