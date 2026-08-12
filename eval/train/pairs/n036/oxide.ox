struct Item { count: Int, price: Int }

fn main() {
    let a = Item { count: 4, price: 3 }
    let b = Item { count: 5, price: 2 }
    print(a.count * a.price + b.count * b.price)
}
