fn main() {
    let v = vec![5, 12, 3, 18, 9];
    let under = v.iter().filter(|&&x| x < 10).count();
    let over = v.len() - under;
    println!("{}", under);
    println!("{}", over);
}
