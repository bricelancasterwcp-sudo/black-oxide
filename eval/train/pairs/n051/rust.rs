fn main() {
    let cs: Vec<char> = "granite".chars().collect();
    println!("{}", cs[0]);
    println!("{}", cs[cs.len() - 1]);
}
