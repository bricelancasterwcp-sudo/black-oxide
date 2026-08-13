fn main() {
    let v = vec(8, 3, 11, 6)
    let lo = 1000000
    let hi = 0
    for x in v {
        if x < lo {
            lo = x
        }
        if x > hi {
            hi = x
        }
    }
    print(lo)
    print(hi - lo)
}
