fn main() {
    let mut found = 0;
    for i in 1..51 {
        if i % 3 == 0 || i % 5 == 0 {
            found += 1;
        }
    }
    println!("{}", found);
}
