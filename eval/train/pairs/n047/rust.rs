fn main() {
    let v: Vec<i64> = (1..11).filter(|x| x % 2 == 0).collect();
    for x in v.iter().rev() {
        println!("{}", x);
    }
}
