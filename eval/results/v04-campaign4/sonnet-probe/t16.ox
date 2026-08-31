fn divide_or_undefined(dividend: Int, divisor: Int) {
    if divisor == 0 {
        print_str("undefined")
    } else {
        print(dividend / divisor)
    }
}

fn main() {
    divide_or_undefined(100, 5)
    divide_or_undefined(100, 0)
    divide_or_undefined(100, 4)
}
