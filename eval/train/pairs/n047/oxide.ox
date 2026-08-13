fn main() {
    let v = vec()
    for i in range(1, 11) {
        if i - (i / 2) * 2 == 0 {
            v = push(v, i)
        }
    }
    let i = len(v) - 1
    while i >= 0 {
        match get(v, i) {
            Some(x) => print(x),
            None => print_str("none"),
        }
        i = i - 1
    }
}
