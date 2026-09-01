fn split_words(phrase: Str) -> Vec<Str> {
    let words = vec()
    let current = ""
    for c in chars(phrase) {
        if c == " " {
            words = push(words, current)
            current = ""
        } else {
            current = concat(current, c)
        }
    }
    push(words, current)
}

fn phrase_report(label: Str, phrase: Str) -> Int {
    let words = split_words(phrase)
    let longest = ""
    let longest_len = 0
    let shortest = 1000
    let long_words = 0
    for w in words {
        let n = str_len(w)
        if n > longest_len {
            longest_len = n
            longest = w
        }
        if n < shortest {
            shortest = n
        }
        if n > 4 {
            long_words += 1
        }
    }
    print_str(label)
    print(len(words))
    print_str(longest)
    print(shortest)
    print(long_words)
    len(words)
}

fn main() {
    let first_count = phrase_report("first", "the harbour lights flickered")
    let second_count = phrase_report("second", "a small boat drifted past silently")
    if first_count > second_count {
        print_str("first")
    } else {
        print_str("second")
    }
}
