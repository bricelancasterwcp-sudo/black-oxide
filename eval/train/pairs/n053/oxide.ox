fn main() {
    let cs = chars("drum")
    let out = ""
    for c in cs {
        out = concat(c, out)
    }
    print_str(out)
    print_str("drum")
}
