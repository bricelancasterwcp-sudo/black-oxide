fn main() {
    let v = vec![10, 20, 30, 40];
    match v.get(2) {
        Some(x) => println!("{}", x),
        None => println!("missing"),
    }
}
