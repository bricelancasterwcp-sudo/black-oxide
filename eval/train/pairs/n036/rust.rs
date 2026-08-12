struct Item { count: i64, price: i64 }

fn main() {
    let a = Item { count: 4, price: 3 };
    let b = Item { count: 5, price: 2 };
    println!("{}", a.count * a.price + b.count * b.price);
}
