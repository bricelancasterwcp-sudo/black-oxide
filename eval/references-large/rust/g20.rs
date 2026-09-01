fn main() {
    let limit: usize = 100;
    let mut is_prime = vec![true; limit + 1];
    is_prime[0] = false;
    is_prime[1] = false;
    let mut p = 2;
    while p * p <= limit {
        if is_prime[p] {
            let mut multiple = p * p;
            while multiple <= limit {
                is_prime[multiple] = false;
                multiple += p;
            }
        }
        p += 1;
    }
    let mut primes: Vec<i64> = Vec::new();
    for n in 2..=limit {
        if is_prime[n] {
            primes.push(n as i64);
        }
    }
    let mut twins = 0;
    for k in 1..primes.len() {
        if primes[k] - primes[k - 1] == 2 {
            twins += 1;
        }
    }
    println!("{}", primes.len());
    println!("{}", primes[primes.len() - 1]);
    println!("{}", primes.iter().sum::<i64>());
    println!("{}", twins);
    println!("{}", primes[9]);
}
