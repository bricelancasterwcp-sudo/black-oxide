enum Shape { Rectangle(Int, Int), Triangle(Int, Int, Int) }

fn perimeter(s: Shape) -> Int {
    match s {
        Rectangle(w, h) => 2 * (w + h),
        Triangle(a, b, c) => a + b + c,
    }
}

fn main() {
    let shapes = vec()
    shapes = push(shapes, Rectangle(3, 4))
    shapes = push(shapes, Triangle(3, 4, 5))
    shapes = push(shapes, Rectangle(2, 5))

    for s in shapes {
        print(perimeter(s))
    }
}
