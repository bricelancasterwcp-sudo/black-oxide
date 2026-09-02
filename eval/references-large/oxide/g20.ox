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
        if is_prime[p] {
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
        if is_prime[n] {
            primes = push(primes, n)
        }
    }
    let twins = 0
    for k in range(1, len(primes)) {
        if primes[k] - primes[k - 1] == 2 {
            twins += 1
        }
    }
    print(len(primes))
    print(primes[len(primes) - 1])
    print(sum(primes))
    print(twins)
    print(primes[9])
}
