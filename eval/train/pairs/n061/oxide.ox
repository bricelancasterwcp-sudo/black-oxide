struct Rect { w: Int, h: Int }

fn main() {
    let r = Rect { w: 9, h: 3 }
    print(r.w * r.h)
    print((r.w + r.h) * 2)
}
