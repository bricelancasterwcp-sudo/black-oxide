fn main() {
    let hits = 0
    for c in chars("banana") {
        if c == "a" {
            hits = hits + 1
        }
    }
    print(hits)
}
