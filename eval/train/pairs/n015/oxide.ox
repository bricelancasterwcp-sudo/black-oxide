fn main() {
    let v = vec(5, 3, 9, 1, 7)
    let count = 0
    for x in v {
        if x > 4 {
            count = count + 1
        }
    }
    print(count)
}
