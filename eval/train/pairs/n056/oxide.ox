fn main() {
    let total = 0
    let failed = 0
    for s in vec("7", "x", "9", "?") {
        match parse_int(s) {
            Some(n) => { total = total + n },
            None => { failed = failed + 1 },
        }
    }
    print(total)
    print(failed)
}
