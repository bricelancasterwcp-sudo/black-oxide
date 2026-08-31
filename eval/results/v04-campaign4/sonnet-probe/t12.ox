fn main() {
    let s = "stack"
    let cs = chars(s)
    cs = reverse(cs)
    let result = ""
    for c in cs {
        result = concat(result, c)
    }
    print_str(result)
}
