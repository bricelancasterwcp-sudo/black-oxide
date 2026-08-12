fn main() {
    let out = ""
    for i in range(1, 4) {
        out = concat(out, int_to_str(i))
    }
    print_str(out)
}
