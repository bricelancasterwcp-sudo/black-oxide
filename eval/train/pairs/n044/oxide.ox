fn main() {
    let v = vec(3, 1, 4, 1, 5)
    let balance = 0
    for x in v {
        balance += x
        print(balance)
    }
}
