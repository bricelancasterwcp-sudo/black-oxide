enum Light { Red, Yellow, Green }

fn main() {
    for l in vec(Green, Red, Yellow) {
        match l {
            Green => print_str("go"),
            Red => print_str("stop"),
            Yellow => print_str("wait"),
        }
    }
}
