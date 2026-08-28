enum Shape { Square(i64), Circle(i64) }

fn area(s: Shape) -> i64 {
    match s {
        Shape::Square(side) => side * side,
        Shape::Circle(r) => 3 * r * r,
    }
}

fn main() {
    println!("{}", area(Shape::Square(4)));
}
