fn main() {
    let v = vec![10, 20];
    for i in [1usize, 4] {
        match v.get(i) {
            Some(x) => println!("{}", x),
            None => println!("none"),
        }
    }
}
