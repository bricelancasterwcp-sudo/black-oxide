fn main() {
    let mut found = 0;
    for i in 1..37 {
        if 36 % i == 0 {
            found += 1;
        }
    }
    println!("{}", found);
}
