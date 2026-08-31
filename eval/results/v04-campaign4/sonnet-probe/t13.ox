fn is_palindrome(s: Str) -> Bool {
    let cs = chars(s)
    let reversed_cs = reverse(cs)
    let rebuilt = ""
    for c in reversed_cs {
        rebuilt = concat(rebuilt, c)
    }
    s == rebuilt
}

fn main() {
    print(is_palindrome("level"))
    print(is_palindrome("stereo"))
    print(is_palindrome("rotor"))
}
