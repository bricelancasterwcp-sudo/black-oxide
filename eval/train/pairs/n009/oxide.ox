fn main() {
    let n = 1234
    let out = 0
    while n > 0 {
        out = out * 10 + n % 10
        n = n / 10
    }
    print(out)
}
