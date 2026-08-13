struct Rect { w: i64, h: i64 }

fn main() {
    let r = Rect { w: 9, h: 3 };
    println!("{}", r.w * r.h);
    println!("{}", (r.w + r.h) * 2);
}
