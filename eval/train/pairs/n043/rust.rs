fn main() {
    let mut v = vec![1, 2, 3, 4, 5];
    let last = v.len() - 1;
    v.swap(0, last);
    for x in &v {
        println!("{}", x);
    }
}
