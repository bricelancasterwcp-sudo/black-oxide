enum Light { Red, Yellow, Green }

fn main() {
    for l in [Light::Green, Light::Red, Light::Yellow] {
        match l {
            Light::Green => println!("go"),
            Light::Red => println!("stop"),
            Light::Yellow => println!("wait"),
        }
    }
}
