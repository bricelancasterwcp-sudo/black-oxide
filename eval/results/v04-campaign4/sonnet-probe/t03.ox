fn main() {
    let a = 252
    let b = 105
    while b > 0 {
        let t = b
        b = a % b
        a = t
    }
    print(a)
}
