fn trend_report(label: Str, series: Vec<Int>) -> Int {
    let rises = 0
    let falls = 0
    let biggest = 0
    let run = 1
    let longest = 1
    for i in range(1, len(series)) {
        let delta = unwrap_or(get(series, i), 0) - unwrap_or(get(series, i - 1), 0)
        if delta > 0 {
            rises += 1
            run += 1
            if run > longest {
                longest = run
            }
        } else {
            if delta < 0 {
                falls += 1
            }
            run = 1
        }
        if delta > biggest {
            biggest = delta
        }
    }
    print_str(label)
    print(rises)
    print(falls)
    print(biggest)
    print(longest)
    longest
}

fn main() {
    let north = vec().push(12).push(15).push(19).push(14).push(14).push(20).push(31).push(30)
    let south = vec().push(40).push(38).push(41).push(45).push(50).push(44)
    let north_run = trend_report("north", north)
    let south_run = trend_report("south", south)
    if north_run > south_run {
        print_str("north")
    } else {
        print_str("south")
    }
}
