fn main() {
    let v = vec(1, 2, 3, 4, 5)
    let last = len(v) - 1
    v = swap(v, 0, last)
    for x in v {
        print(x)
    }
}
