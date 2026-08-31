fn main() {
    let s = "mississippi"
    print(count_if(chars(s), |c| c == "s"))
    let seen = vec()
    for c in chars(s) {
        if !contains(seen, clone(c)) {
            seen = push(seen, c)
        }
    }
    print(len(seen))
}
