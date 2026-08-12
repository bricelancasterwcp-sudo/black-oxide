fn main() {
    let mut picked = Vec::new();
    for x in 1..11 {
        if x % 3 == 0 {
            picked.push(x);
        }
    }
    let total: i64 = picked.iter().sum();
    println!("{}", total);
}
