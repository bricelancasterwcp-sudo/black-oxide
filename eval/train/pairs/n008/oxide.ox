fn main() {
    let found = 0
    for i in range(1, 51) {
        if i % 3 == 0 || i % 5 == 0 {
            found = found + 1
        }
    }
    print(found)
}
