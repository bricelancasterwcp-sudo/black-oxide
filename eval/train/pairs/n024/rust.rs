fn main() {
    let hits = "banana".chars().filter(|c| *c == 'a').count();
    println!("{}", hits);
}
