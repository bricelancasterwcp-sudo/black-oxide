fn main() {
    let text = "order 47 shipped on 2026-03-15, invoice 1290 paid"
    let digit_set = chars("0123456789")
    let letter_set = chars("abcdefghijklmnopqrstuvwxyz")
    let letters = 0
    let digits = 0
    let spaces = 0
    let others = 0
    let digit_run = 0
    let longest_digit_run = 0
    let digits_only = ""
    for c in chars(text) {
        if contains(digit_set, clone(c)) {
            digits += 1
            digit_run += 1
            digits_only = concat(digits_only, c)
            if digit_run > longest_digit_run {
                longest_digit_run = digit_run
            }
        } else {
            digit_run = 0
            if contains(letter_set, clone(c)) {
                letters += 1
            } else if c == " " {
                spaces += 1
            } else {
                others += 1
            }
        }
    }
    print(str_len(text))
    print(letters)
    print(digits)
    print(spaces)
    print(others)
    print(longest_digit_run)
    print_str(digits_only)
}
