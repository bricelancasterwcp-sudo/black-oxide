fn sum_divisors(n: Int) -> Int {
    let total = 0
    let i = 1
    while i < n {
        if n % i == 0 {
            total += i
        }
        i += 1
    }
    total
}

fn main() {
    for n in range(1, 1000) {
        if sum_divisors(n) == n {
            print(n)
        }
    }
}
