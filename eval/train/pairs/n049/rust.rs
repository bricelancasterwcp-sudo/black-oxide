fn main() {
    let v = vec![8, 3, 11, 6];
    let lo = *v.iter().min().unwrap();
    let hi = *v.iter().max().unwrap();
    println!("{}", lo);
    println!("{}", hi - lo);
}
