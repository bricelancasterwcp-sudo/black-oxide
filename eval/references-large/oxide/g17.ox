fn main() {
    let left = vec().push(2).push(5).push(9).push(14).push(21).push(30)
    let right = vec().push(1).push(5).push(8).push(15).push(22)
    let merged = vec()
    let i = 0
    let j = 0
    while i < len(left) && j < len(right) {
        if left[i] <= right[j] {
            merged = push(merged, left[i])
            i += 1
        } else {
            merged = push(merged, right[j])
            j += 1
        }
    }
    while i < len(left) {
        merged = push(merged, left[i])
        i += 1
    }
    while j < len(right) {
        merged = push(merged, right[j])
        j += 1
    }
    let sorted = true
    let duplicates = 0
    for k in range(1, len(merged)) {
        let current = merged[k]
        let previous = merged[k - 1]
        if current < previous {
            sorted = false
        }
        if current == previous {
            duplicates += 1
        }
    }
    print(len(merged))
    print(merged[0])
    print(merged[len(merged) - 1])
    print(sum(merged))
    print(sorted)
    print(duplicates)
}
