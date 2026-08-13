fn main() {
    let best = ""
    for s in vec("fig", "banana", "kiwi") {
        if str_len(s) > str_len(best) {
            best = s
        }
    }
    let n = str_len(best)
    print_str(best)
    print(n)
}
