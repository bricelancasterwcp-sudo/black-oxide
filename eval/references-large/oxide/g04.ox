fn factor_report(n: Int) -> Bool {
    let remaining = n
    let factors = vec()
    let d = 2
    while d * d <= remaining {
        if remaining % d == 0 {
            factors = push(factors, d)
            while remaining % d == 0 {
                remaining = remaining / d
            }
        }
        d += 1
    }
    if remaining > 1 {
        factors = push(factors, remaining)
    }
    let prime = len(factors) == 1 && unwrap_or(get(factors, 0), 0) == n
    print(n)
    print(len(factors))
    print(sum(factors))
    print(unwrap_or(max(factors), 0))
    print(prime)
    prime
}

fn main() {
    let numbers = vec().push(360).push(97).push(1024).push(561).push(143).push(2003)
    let primes = 0
    for n in numbers {
        if factor_report(n) {
            primes += 1
        }
    }
    print(primes)
}
