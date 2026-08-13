fn main() {
    let v = vec(12, 5, 20, 8, 17)
    let best = 0
    for x in v {
        if x > best {
            best = x
        }
    }
    let second = 0
    for x in v {
        if x > second && x < best {
            second = x
        }
    }
    print(best)
    print(second)
}
