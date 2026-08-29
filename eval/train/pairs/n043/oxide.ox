fn main() {
    let v = vec(1, 2, 3, 4, 5)
    let last = len(v) - 1
    let out = vec()
    let i = 0
    for x in v {
        if i == 0 {
            out = push(out, unwrap_or(get(v, last), x))
        } else {
            if i == last {
                out = push(out, unwrap_or(get(v, 0), x))
            } else {
                out = push(out, x)
            }
        }
        i = i + 1
    }
    for y in out {
        print(y)
    }
}
