fn main() {
    let prime = true
    for i in range(2, 91) {
        if 91 % i == 0 {
            prime = false
        }
    }
    if prime {
        print_str("yes")
    } else {
        print_str("no")
    }
}
