fn main() {
    let v = vec![5, 3, 9, 1, 7];
    let mut least = 9999;
    for x in &v {
        if *x < least {
            least = *x;
        }
    }
    println!("{}", least);
}
