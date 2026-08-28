fn main() {
    let mut prime = true;
    for i in 2..91 {
        if 91 % i == 0 {
            prime = false;
        }
    }
    if prime {
        println!("yes");
    } else {
        println!("no");
    }
}
