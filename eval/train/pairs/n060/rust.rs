fn main() {
    let mut total = 0u32;
    let mut count = 0;
    for c in "a1b22".chars() {
        if let Some(d) = c.to_digit(10) {
            total += d;
            count += 1;
        }
    }
    println!("{}", total);
    println!("{}", count);
}
