fn main() {
    let mut counter: i64 = 9;
    let mut halvings = 0;
    let mut boosts = 0;
    let mut triples = 0;
    let mut largest = counter;
    let mut largest_step = 0;
    let mut lowest = counter;
    let mut total = 0;
    let mut small_steps = 0;
    let mut step = 1;
    while step <= 30 {
        if counter % 2 == 0 {
            counter /= 2;
            halvings += 1;
        } else if counter % 3 == 0 {
            counter += 5;
            boosts += 1;
        } else {
            counter = (counter * 3 + 1) % 1000;
            triples += 1;
        }
        if counter > largest {
            largest = counter;
            largest_step = step;
        }
        if counter < lowest {
            lowest = counter;
        }
        if counter < 10 {
            small_steps += 1;
        }
        total += counter;
        step += 1;
    }
    println!("{}", counter);
    println!("{}", halvings);
    println!("{}", boosts);
    println!("{}", triples);
    println!("{}", largest);
    println!("{}", largest_step);
    println!("{}", lowest);
    println!("{}", total);
    println!("{}", small_steps);
    if counter > 100 {
        println!("high");
    } else {
        println!("low");
    }
}
