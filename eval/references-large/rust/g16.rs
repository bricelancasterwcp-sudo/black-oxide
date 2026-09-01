fn main() {
    let mut n: i64 = 44;
    let mut steps = 0;
    let mut largest = n;
    let mut smallest = n;
    let mut total = 0;
    let mut evens = 0;
    let mut digit_total = 0;
    let mut previous = n;
    let mut reached_one = false;
    while steps < 50 {
        let mut next = 0;
        let mut rest = n;
        while rest > 0 {
            let digit = rest % 10;
            next += digit * digit;
            digit_total += digit;
            rest /= 10;
        }
        previous = n;
        n = next;
        steps += 1;
        if n > largest {
            largest = n;
        }
        if n < smallest {
            smallest = n;
        }
        if n % 2 == 0 {
            evens += 1;
        }
        total += n;
        if n == 1 {
            reached_one = true;
            break;
        }
    }
    println!("{}", steps);
    println!("{}", n);
    println!("{}", previous);
    println!("{}", largest);
    println!("{}", smallest);
    println!("{}", total);
    println!("{}", evens);
    println!("{}", digit_total);
    println!("{}", reached_one);
}
