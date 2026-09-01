enum Shape { Rect(Int, Int), Square(Int), Circle(Int) }

struct Described { kind: Str, area: Int }

fn describe(shape: Shape) -> Described {
    match shape {
        Rect(w, h) => Described { kind: "rect", area: w * h },
        Square(s) => Described { kind: "square", area: s * s },
        Circle(r) => Described { kind: "circle", area: 3 * r * r },
    }
}

fn main() {
    let shapes = vec().push(Rect(7, 4)).push(Square(5)).push(Circle(3)).push(Rect(2, 9))
    let total = 0
    let largest = 0
    let largest_kind = ""
    for s in shapes {
        let d = describe(s)
        print_str(d.kind)
        print(d.area)
        total += d.area
        if d.area > largest {
            largest = d.area
            largest_kind = d.kind
        }
    }
    print(total)
    print_str(largest_kind)
}
