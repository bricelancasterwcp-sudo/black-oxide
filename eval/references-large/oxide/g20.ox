fn main() {
    let limit = 100
    let is_prime = vec()
    for i in range(0, limit + 1) {
        is_prime = push(is_prime, true)
    }
    is_prime = set(is_prime, 0, false)
    is_prime = set(is_prime, 1, false)
    let p = 2
    while p * p <= limit {
        if unwrap_or(get(is_prime, p), false) {
            let multiple = p * p
            while multiple <= limit {
                is_prime = set(is_prime, multiple, false)
                multiple += p
            }
        }
        p += 1
    }
    let primes = vec()
    for n in range(2, limit + 1) {
        if unwrap_or(get(is_prime, n), false) {
            primes = push(primes, n)
        }
    }
    let twins = 0
    for k in range(1, len(primes)) {
        if unwrap_or(get(primes, k), 0) - unwrap_or(get(primes, k - 1), 0) == 2 {
            twins += 1
        }
    }
    print(len(primes))
    print(unwrap_or(get(primes, len(primes) - 1), 0))
    print(sum(primes))
    print(twins)
    print(unwrap_or(get(primes, 9), 0))
}
