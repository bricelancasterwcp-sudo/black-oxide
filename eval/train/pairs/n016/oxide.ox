fn main() {
    let picked = vec()
    for x in range(1, 11) {
        if x % 3 == 0 {
            picked = push(picked, x)
        }
    }
    let total = 0
    for x in picked {
        total = total + x
    }
    print(total)
}
