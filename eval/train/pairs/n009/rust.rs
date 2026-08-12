fn main() {
    let mut n = 1234;
    let mut out = 0;
    while n > 0 {
        out = out * 10 + n % 10;
        n /= 10;
    }
    println!("{}", out);
}
