fn main() {
    let words = 1
    for c in chars("when in doubt go home") {
        if c == " " {
            words = words + 1
        }
    }
    print(words)
    print(str_len("when in doubt go home"))
}
