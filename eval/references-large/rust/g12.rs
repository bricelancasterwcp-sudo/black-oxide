enum Shape {
    Rect(i64, i64),
    Square(i64),
    Circle(i64),
}

fn describe(shape: &Shape) -> (String, i64) {
    match shape {
        Shape::Rect(w, h) => ("rect".to_string(), w * h),
        Shape::Square(s) => ("square".to_string(), s * s),
        Shape::Circle(r) => ("circle".to_string(), 3 * r * r),
    }
}

fn main() {
    let shapes = vec![
        Shape::Rect(7, 4),
        Shape::Square(5),
        Shape::Circle(3),
        Shape::Rect(2, 9),
    ];
    let mut total = 0;
    let mut largest = 0;
    let mut largest_kind = String::new();
    for s in &shapes {
        let (kind, area) = describe(s);
        println!("{}", kind);
        println!("{}", area);
        total += area;
        if area > largest {
            largest = area;
            largest_kind = kind;
        }
    }
    println!("{}", total);
    println!("{}", largest_kind);
}
