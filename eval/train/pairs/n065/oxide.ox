fn main() {
    let v = vec(6, 11, 3, 14, 9)
    let above = 0
    let best = unwrap_or(max(v), 0)
    for x in v {
        if x > 5 {
            above += 1
        }
    }
    print(above)
    print(best)
}
