fn main() {
    let hits = 0
    for c in chars("sequence") {
        if c == "a" || c == "e" || c == "i" || c == "o" || c == "u" {
            hits = hits + 1
        }
    }
    print(hits)
}
