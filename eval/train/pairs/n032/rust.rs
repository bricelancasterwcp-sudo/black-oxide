struct Point { x: i64, y: i64 }

fn main() {
    let p = Point { x: 1, y: 5 };
    let q = Point { x: 10, ..p };
    println!("{}", q.x + q.y);
}
