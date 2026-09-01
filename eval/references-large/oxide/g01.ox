fn summarize(label: Str, readings: Vec<Int>) {
    let count = len(readings)
    let total = sum(readings)
    let average = total / count
    let above = 0
    for r in readings {
        if r > average {
            above += 1
        }
    }
    let smallest = unwrap_or(min(readings), 0)
    let largest = unwrap_or(max(readings), 0)
    print_str(label)
    print(count)
    print(average)
    print(above)
    print(largest - smallest)
}

fn main() {
    let group_a = vec().push(120).push(95).push(143).push(87).push(210).push(156).push(99)
    let group_b = vec().push(175).push(132).push(88).push(240).push(119).push(167)
    let total_a = sum(group_a)
    let total_b = sum(group_b)
    summarize("A", group_a)
    summarize("B", group_b)
    if total_a > total_b {
        print_str("A")
    } else {
        print_str("B")
    }
}
