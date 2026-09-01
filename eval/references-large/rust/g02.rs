fn report(word: &str) -> bool {
    let reversed: String = word.chars().rev().collect();
    let vowels = word.chars().filter(|c| "aeiou".contains(*c)).count();
    let mut distinct: Vec<char> = Vec::new();
    for c in word.chars() {
        if !distinct.contains(&c) {
            distinct.push(c);
        }
    }
    let palindrome = reversed == word;
    println!("{}", word);
    println!("{}", word.chars().count());
    println!("{}", reversed);
    println!("{}", palindrome);
    println!("{}", vowels);
    println!("{}", distinct.len());
    palindrome
}

fn main() {
    let mut palindromes = 0;
    for w in ["rotor", "banana", "level", "quiet", "deified", "system", "civic"] {
        if report(w) {
            palindromes += 1;
        }
    }
    println!("{}", palindromes);
}
