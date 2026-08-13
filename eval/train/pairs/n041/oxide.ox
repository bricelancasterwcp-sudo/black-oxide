fn main() {
    let remaining = vec(9, 2, 7, 4)
    while len(remaining) > 0 {
        let m = 1000000
        for x in remaining {
            if x < m {
                m = x
            }
        }
        print(m)
        let rest = vec()
        let removed = false
        for x in remaining {
            if x == m && removed == false {
                removed = true
            } else {
                rest = push(rest, x)
            }
        }
        remaining = rest
    }
}
