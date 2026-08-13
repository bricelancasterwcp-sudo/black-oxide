fn main() {
    let v = vec(6, 11, 3, 14, 9)
    let above = 0
    let best = 0
    for x in v {
        if x > 5 {
            above = above + 1
        }
        if x > best {
            best = x
        }
    }
    print(above)
    print(best)
}
