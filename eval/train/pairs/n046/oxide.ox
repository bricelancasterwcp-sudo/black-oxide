fn main() {
    let v = vec(5, 12, 3, 18, 9)
    let under = count_if(v, x -> x < 10)
    print(under)
    print(len(v) - under)
}
