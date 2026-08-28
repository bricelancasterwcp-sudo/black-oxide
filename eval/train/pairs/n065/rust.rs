fn main() {
    let v = vec![6, 11, 3, 14, 9];
    println!("{}", v.iter().filter(|&&x| x > 5).count());
    println!("{}", v.iter().max().unwrap());
}
