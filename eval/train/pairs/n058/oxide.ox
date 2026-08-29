fn main() {
    let cs = chars("coffee")
    let reported = vec()
    for c in cs {
        let count = count(cs, c)
        let seen = contains(reported, c)
        if count > 1 && seen == false {
            print_str(c)
            reported = push(reported, c)
        }
    }
}
