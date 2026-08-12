fn main() {
    let v = vec![1, 2];
    match v.get(5) {
        Some(x) => println!("{}", x),
        None => println!("none"),
    }
}
