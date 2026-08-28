struct Line { units: Int, price: Int }

fn main() {
    let total = 0
    for l in vec(Line { units: 4, price: 3 }, Line { units: 5, price: 2 }) {
        let value = l.units * l.price
        print(value)
        total += value
    }
    print(total)
}
