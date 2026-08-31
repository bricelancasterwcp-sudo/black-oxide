fn main() {
    let s = "mississippi"
    print(count(chars(s), "s"))

    let seen = vec()
    for c in chars(s) {
        if !contains(seen, c) {
            seen = push(seen, c)
        }
    }
    print(len(seen))
}
