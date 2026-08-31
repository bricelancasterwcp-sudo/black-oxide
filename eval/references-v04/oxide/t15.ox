fn main() {
    let v = vec("12", "x", "30")
    let sum = 0
    let failed = 0
    for s in v {
        match parse_int(s) {
            Some(n) => { sum += n },
            None => { failed += 1 },
        }
    }
    print(sum)
    print(failed)
}
