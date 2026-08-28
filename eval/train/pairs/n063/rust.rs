struct Line { units: i64, price: i64 }

fn main() {
    let lines = [Line { units: 4, price: 3 }, Line { units: 5, price: 2 }];
    let mut total = 0;
    for l in &lines {
        let value = l.units * l.price;
        println!("{}", value);
        total += value;
    }
    println!("{}", total);
}
