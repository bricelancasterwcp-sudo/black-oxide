fn main() {
    let mut out = String::new();
    for i in 1..4 {
        out.push_str(&i.to_string());
    }
    println!("{}", out);
}
