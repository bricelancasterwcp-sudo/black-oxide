fn main() {
    let i = 0
    for c in chars("banana") {
        if c == "n" {
            print(i)
        }
        i += 1
    }
}
