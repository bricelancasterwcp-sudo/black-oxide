fn main() {
    let v = vec()
    v = push(v, 4)
    v = push(v, 1)
    v = push(v, 7)
    v = push(v, 3)
    v = push(v, 9)
    v = push(v, 2)

    let kept = filter(v, |x| x > 3)
    for x in kept {
        print(x)
    }
    print(len(kept))
}
