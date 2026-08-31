fn main() {
    let v = vec()
    v = push(v, 1)
    v = push(v, 2)
    v = push(v, 3)
    v = push(v, 4)
    v = push(v, 5)
    v = reverse(v)
    for x in v {
        print(x)
    }
}
