fn rev_str(s: Str) -> Str {
    let out = ""
    for c in chars(s) {
        out = concat(c, out)
    }
    out
}

fn is_vowel(c: Str) -> Bool {
    c == "a" || c == "e" || c == "i" || c == "o" || c == "u"
}

fn report(word: Str) -> Bool {
    let reversed = rev_str(word)
    let vowels = count_if(chars(word), |c| is_vowel(c))
    let distinct = vec()
    for c in chars(word) {
        if !contains(distinct, clone(c)) {
            distinct = push(distinct, c)
        }
    }
    let palindrome = reversed == word
    print_str(word)
    print(str_len(word))
    print_str(reversed)
    print(palindrome)
    print(vowels)
    print(len(distinct))
    palindrome
}

fn main() {
    let words = vec().push("rotor").push("banana").push("level").push("quiet").push("deified").push("system").push("civic")
    let palindromes = 0
    for w in words {
        if report(w) {
            palindromes += 1
        }
    }
    print(palindromes)
}
