fn main() {
    let v = vec(5, 12, 3, 18, 9)
    let under = 0
    let over = 0
    for x in v {
        if x < 10 {
            under += 1
        } else {
            over += 1
        }
    }
    print(under)
    print(over)
}
