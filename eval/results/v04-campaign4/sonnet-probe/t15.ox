fn main() {
    let total = 0
    let failed = 0

    match parse_int("12") {
        Some(n) => { total += n },
        None => { failed += 1 },
    }
    match parse_int("x") {
        Some(n) => { total += n },
        None => { failed += 1 },
    }
    match parse_int("30") {
        Some(n) => { total += n },
        None => { failed += 1 },
    }

    print(total)
    print(failed)
}
