fn main() {
    let mut vowels = 0;
    let mut others = 0;
    for c in "keyboard".chars() {
        if "aeiou".contains(c) {
            vowels += 1;
        } else {
            others += 1;
        }
    }
    println!("{}", vowels);
    println!("{}", others);
}
