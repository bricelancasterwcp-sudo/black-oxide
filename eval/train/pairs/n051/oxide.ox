fn main() {
    let cs = chars("granite")
    print_str(unwrap_or(get(cs, 0), "none"))
    print_str(unwrap_or(get(cs, len(cs) - 1), "none"))
}
