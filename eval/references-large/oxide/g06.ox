fn band_report(label: Str, scores: Vec<Int>) -> Int {
    let top = 0
    let high = 0
    let mid = 0
    let pass = 0
    let fail = 0
    for s in scores {
        if s >= 90 {
            high += 1
        } else if s >= 80 {
            mid += 1
        } else if s >= 70 {
            pass += 1
        } else {
            fail += 1
        }
        if s > top {
            top = s
        }
    }
    let average = sum(scores) / len(scores)
    print_str(label)
    print(high)
    print(mid)
    print(pass)
    print(fail)
    print(top)
    print(average)
    average
}

fn main() {
    let morning = vec().push(94).push(71).push(88).push(65).push(92).push(79).push(83)
    let evening = vec().push(55).push(90).push(77).push(84).push(68).push(99)
    let morning_average = band_report("morning", morning)
    let evening_average = band_report("evening", evening)
    if morning_average > evening_average {
        print_str("morning")
    } else {
        print_str("evening")
    }
}
