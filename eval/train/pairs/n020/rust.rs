fn main() {
    let v = vec![4, 8, 15, 16, 23, 42];
    let total: i64 = v.iter().sum();
    println!("{}", total / v.len() as i64);
}
