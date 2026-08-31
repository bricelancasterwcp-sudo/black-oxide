fn main() {
    let kept = filter(vec(4, 1, 7, 3, 9, 2), |x| x > 3)
    for y in kept {
        print(y)
    }
    print(len(kept))
}
