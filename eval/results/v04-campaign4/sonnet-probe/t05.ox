fn main() {
    let a = 1
    let b = 1
    let i = 2
    while i < 20 {
        let next = a + b
        a = b
        b = next
        i += 1
    }
    print(b)
}
