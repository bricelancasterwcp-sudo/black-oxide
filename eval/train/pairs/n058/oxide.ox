fn main() {
    let cs = chars("coffee")
    let reported = vec()
    for c in cs {
        let count = 0
        for d in cs {
            if d == c {
                count = count + 1
            }
        }
        let seen = contains(reported, c)
        if count > 1 && seen == false {
            print_str(c)
            reported = push(reported, c)
        }
    }
}
