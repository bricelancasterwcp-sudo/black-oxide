fn main() {
    let v = vec![7, 4, 9, 10];
    let mut evens = 0;
    for x in &v {
        if x % 2 == 0 {
            evens += x;
        } else {
            println!("{}", x * 2);
        }
    }
    println!("{}", evens);
}
