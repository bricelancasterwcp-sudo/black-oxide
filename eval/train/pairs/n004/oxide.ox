fn main() {
    let a = 1
    let b = 1
    for i in range(2, 10) {
        let next = a + b
        a = b
        b = next
    }
    print(b)
}
