enum Light { Red, Yellow, Green }

fn main() {
    let l = Green
    match l {
        Green => print_str("go"),
        Yellow => print_str("wait"),
        Red => print_str("stop"),
    }
}
