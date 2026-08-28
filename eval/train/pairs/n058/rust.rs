fn main() {
    let cs: Vec<char> = "coffee".chars().collect();
    let mut reported: Vec<char> = Vec::new();
    for &c in &cs {
        let count = cs.iter().filter(|&&d| d == c).count();
        if count > 1 && !reported.contains(&c) {
            println!("{}", c);
            reported.push(c);
        }
    }
}
