fn main() {
    let values = vec().push(4).push(4).push(4).push(7).push(7).push(2).push(9).push(9).push(9).push(9).push(1).push(1).push(5)
    let longest_run = 1
    let longest_value = values[0]
    let current_run = 1
    let distinct = vec()
    let first_duplicate = -1
    let sorted = true
    for i in range(0, len(values)) {
        let current = values[i]
        if i > 0 {
            let previous = values[i - 1]
            if current == previous {
                current_run += 1
            } else {
                current_run = 1
            }
            if current_run > longest_run {
                longest_run = current_run
                longest_value = current
            }
            if current < previous {
                sorted = false
            }
        }
        if contains(distinct, current) {
            if first_duplicate == -1 {
                first_duplicate = i
            }
        } else {
            distinct = push(distinct, current)
        }
    }
    print(len(values))
    print(longest_run)
    print(longest_value)
    print(len(distinct))
    print(first_duplicate)
    print(sorted)
}
