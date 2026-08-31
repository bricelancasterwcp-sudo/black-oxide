fn main() {
    let v = vec![10, 20, 30];
    for i in [1usize, 5usize] {
        println!("{}", v.get(i).copied().unwrap_or(-1));
    }
}
