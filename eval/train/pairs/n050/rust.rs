fn main() {
    let mut v = vec![2, 9, 5];
    v.sort();
    v.reverse();
    for x in &v {
        println!("{}", x);
    }
}
