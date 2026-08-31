fn is_prime(n: Int) -> Bool {
    if n < 2 {
        false
    } else {
        let i = 2
        let result = true
        while i * i <= n {
            if n % i == 0 {
                result = false
                break
            }
            i += 1
        }
        result
    }
}

fn main() {
    let prime_count = 0
    for n in range(0, 100) {
        if is_prime(n) {
            prime_count += 1
        }
    }
    print(prime_count)
}
