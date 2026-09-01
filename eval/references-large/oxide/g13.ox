fn main() {
    let counter = 9
    let halvings = 0
    let boosts = 0
    let triples = 0
    let largest = counter
    let largest_step = 0
    let lowest = counter
    let total = 0
    let small_steps = 0
    let step = 1
    while step <= 30 {
        if counter % 2 == 0 {
            counter = counter / 2
            halvings += 1
        } else if counter % 3 == 0 {
            counter += 5
            boosts += 1
        } else {
            counter = (counter * 3 + 1) % 1000
            triples += 1
        }
        if counter > largest {
            largest = counter
            largest_step = step
        }
        if counter < lowest {
            lowest = counter
        }
        if counter < 10 {
            small_steps += 1
        }
        total += counter
        step += 1
    }
    print(counter)
    print(halvings)
    print(boosts)
    print(triples)
    print(largest)
    print(largest_step)
    print(lowest)
    print(total)
    print(small_steps)
    if counter > 100 {
        print_str("high")
    } else {
        print_str("low")
    }
}
