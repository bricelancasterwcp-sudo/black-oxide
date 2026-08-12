fn main() {
    let hits = "sequence".chars().filter(|c| "aeiou".contains(*c)).count();
    println!("{}", hits);
}
