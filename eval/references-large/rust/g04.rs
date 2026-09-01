fn factor_report(n: i64) -> bool {
    let mut remaining = n;
    let mut factors: Vec<i64> = Vec::new();
    let mut d = 2;
    while d * d <= remaining {
        if remaining % d == 0 {
            factors.push(d);
            while remaining % d == 0 {
                remaining /= d;
            }
        }
        d += 1;
    }
    if remaining > 1 {
        factors.push(remaining);
    }
    let prime = factors.len() == 1 && factors[0] == n;
    println!("{}", n);
    println!("{}", factors.len());
    println!("{}", factors.iter().sum::<i64>());
    println!("{}", factors.iter().max().unwrap());
    println!("{}", prime);
    prime
}

fn main() {
    let mut primes = 0;
    for n in [360, 97, 1024, 561, 143, 2003] {
        if factor_report(n) {
            primes += 1;
        }
    }
    println!("{}", primes);
}
