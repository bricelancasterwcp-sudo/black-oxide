fn main() {
    let v = vec()
    v = push(v, 5)
    v = push(v, 3)
    v = push(v, 8)
    v = push(v, 1)
    v = push(v, 9)
    v = push(v, 2)

    let sorted = sort(v)
    for x in sorted {
        print(x)
    }
}
