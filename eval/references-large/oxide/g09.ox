fn station_report(label: Str, celsius: Vec<Int>) -> Int {
    let freezing = 0
    let hot = 0
    let hottest = -1000
    let coldest = 1000
    for c in celsius {
        let f = c * 9 / 5 + 32
        if c <= 0 {
            freezing += 1
        }
        if c >= 30 {
            hot += 1
        }
        if f > hottest {
            hottest = f
        }
        if f < coldest {
            coldest = f
        }
    }
    let average = sum(celsius) / len(celsius)
    print_str(label)
    print(freezing)
    print(hot)
    print(hottest)
    print(coldest)
    print(average)
    average
}

fn main() {
    let alpha = vec().push(-5).push(12).push(30).push(22).push(0).push(35).push(18)
    let beta = vec().push(8).push(-12).push(5).push(41).push(27)
    let alpha_average = station_report("alpha", alpha)
    let beta_average = station_report("beta", beta)
    if alpha_average > beta_average {
        print_str("alpha")
    } else {
        print_str("beta")
    }
}
