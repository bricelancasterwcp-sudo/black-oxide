fn main() {
    let v = vec![5, 3, 9, 1, 7];
    let mut best = 0;
    for x in &v {
        if *x > best {
            best = *x;
        }
    }
    println!("{}", best);
}
