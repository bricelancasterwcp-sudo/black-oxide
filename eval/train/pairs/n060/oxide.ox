fn main() {
    let total = 0
    let count = 0
    for c in chars("a1b22") {
        let n = unwrap_or(parse_int(c), -1)
        if n >= 0 {
            total = total + n
            count = count + 1
        }
    }
    print(total)
    print(count)
}
