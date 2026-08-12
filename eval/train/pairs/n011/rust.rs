fn main() {
    let mut v = Vec::new();
    for i in 1..7 {
        v.push(i * 4);
    }
    let total: i64 = v.iter().sum();
    println!("{}", total);
}
