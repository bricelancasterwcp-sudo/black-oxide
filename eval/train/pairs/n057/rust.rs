fn main() {
    let mut best = "";
    for s in ["fig", "banana", "kiwi"] {
        if s.len() > best.len() {
            best = s;
        }
    }
    println!("{}", best);
    println!("{}", best.len());
}
