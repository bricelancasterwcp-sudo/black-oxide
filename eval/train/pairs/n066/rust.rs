fn main() {
    let v = vec![9, 2, 12, 5, 16];
    let mut kept = 0;
    for x in &v {
        if *x < 10 {
            println!("{}", x);
            kept += 1;
        }
    }
    println!("{}", kept);
}
