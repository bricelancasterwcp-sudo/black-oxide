enum Light { Red, Yellow, Green }

fn main() {
    let l = Light::Green;
    match l {
        Light::Green => println!("go"),
        Light::Yellow => println!("wait"),
        Light::Red => println!("stop"),
    }
}
