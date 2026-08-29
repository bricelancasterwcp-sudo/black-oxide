fn main() {
    let vowels = 0
    let others = 0
    for c in chars("keyboard") {
        if c == "a" || c == "e" || c == "i" || c == "o" || c == "u" {
            vowels += 1
        } else {
            others += 1
        }
    }
    print(vowels)
    print(others)
}
