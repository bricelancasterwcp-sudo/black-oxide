fn main() {
    let left = vec().push(2).push(5).push(9).push(14).push(21).push(30)
    let right = vec().push(1).push(5).push(8).push(15).push(22)
    let merged = vec()
    let i = 0
    let j = 0
    while i < len(left) && j < len(right) {
        if unwrap_or(get(left, i), 0) <= unwrap_or(get(right, j), 0) {
            merged = push(merged, unwrap_or(get(left, i), 0))
            i += 1
        } else {
            merged = push(merged, unwrap_or(get(right, j), 0))
            j += 1
        }
    }
    while i < len(left) {
        merged = push(merged, unwrap_or(get(left, i), 0))
        i += 1
    }
    while j < len(right) {
        merged = push(merged, unwrap_or(get(right, j), 0))
        j += 1
    }
    let sorted = true
    let duplicates = 0
    for k in range(1, len(merged)) {
        let current = unwrap_or(get(merged, k), 0)
        let previous = unwrap_or(get(merged, k - 1), 0)
        if current < previous {
            sorted = false
        }
        if current == previous {
            duplicates += 1
        }
    }
    print(len(merged))
    print(unwrap_or(get(merged, 0), 0))
    print(unwrap_or(get(merged, len(merged) - 1), 0))
    print(sum(merged))
    print(sorted)
    print(duplicates)
}
