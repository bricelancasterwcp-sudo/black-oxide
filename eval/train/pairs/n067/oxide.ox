fn main() {
    let evens = 0
    for x in vec(7, 4, 9, 10) {
        if x - (x / 2) * 2 == 0 {
            evens = evens + x
        } else {
            print(x * 2)
        }
    }
    print(evens)
}
