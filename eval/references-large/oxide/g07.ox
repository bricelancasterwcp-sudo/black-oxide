fn index_of(letters: Vec<Str>, target: Str) -> Int {
    let i = 0
    let found = -1
    for c in letters {
        if c == target {
            found = i
            break
        }
        i += 1
    }
    found
}

fn shift_word(word: Str, by: Int) -> Str {
    let letters = chars("abcdefghijklmnopqrstuvwxyz")
    let out = ""
    for c in chars(word) {
        let idx = index_of(letters, c)
        let moved = (idx + by + 26) % 26
        out = concat(out, letters[moved])
    }
    out
}

fn main() {
    let words = vec().push("ferry").push("oxide").push("cargo")
    for w in words {
        let encoded = shift_word(w, 3)
        let decoded = shift_word(encoded, -3)
        let rotated = shift_word(w, 13)
        let restored = shift_word(rotated, 13)
        print_str(w)
        print_str(encoded)
        print_str(decoded)
        print(decoded == w)
        print_str(rotated)
        print(restored == w)
    }
}
