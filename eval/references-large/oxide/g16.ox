fn main() {
    let n = 44
    let steps = 0
    let largest = n
    let smallest = n
    let total = 0
    let evens = 0
    let digit_total = 0
    let previous = n
    let reached_one = false
    while steps < 50 {
        let next = 0
        let rest = n
        while rest > 0 {
            let digit = rest % 10
            next += digit * digit
            digit_total += digit
            rest = rest / 10
        }
        previous = n
        n = next
        steps += 1
        if n > largest {
            largest = n
        }
        if n < smallest {
            smallest = n
        }
        if n % 2 == 0 {
            evens += 1
        }
        total += n
        if n == 1 {
            reached_one = true
            break
        }
    }
    print(steps)
    print(n)
    print(previous)
    print(largest)
    print(smallest)
    print(total)
    print(evens)
    print(digit_total)
    print(reached_one)
}
