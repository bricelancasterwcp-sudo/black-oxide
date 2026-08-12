fn second(v: Vec<Int>) -> Option<Int> {
    let x = get(v, 1)?
    Some(x)
}

fn main() {
    match second(vec(7, 8, 9)) {
        Some(n) => print(n),
        None => print_str("none"),
    }
}
