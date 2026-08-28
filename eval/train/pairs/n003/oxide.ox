fn main() {
    let found = 0
    for i in range(1, 37) {
        if 36 % i == 0 {
            found += 1
        }
    }
    print(found)
}
