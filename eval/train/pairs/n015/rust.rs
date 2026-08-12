fn main() {
    let v = vec![5, 3, 9, 1, 7];
    let count = v.iter().filter(|x| **x > 4).count();
    println!("{}", count);
}
