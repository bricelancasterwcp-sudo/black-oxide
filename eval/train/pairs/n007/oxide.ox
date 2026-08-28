fn main() {
    let n = 9875
    let total = 0
    while n > 0 {
        total = total + n % 10
        n = n / 10
    }
    print(total)
}
