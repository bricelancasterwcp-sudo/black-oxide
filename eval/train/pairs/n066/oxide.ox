fn main() {
    let kept = 0
    for x in vec(9, 2, 12, 5, 16) {
        if x < 10 {
            print(x)
            kept = kept + 1
        }
    }
    print(kept)
}
