fn second(v: &[i64]) -> Option<i64> {
    let x = v.get(1)?;
    Some(*x)
}

fn main() {
    match second(&[7, 8, 9]) {
        Some(n) => println!("{}", n),
        None => println!("none"),
    }
}
