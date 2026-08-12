struct Rect { w: i64, h: i64 }

fn main() {
    let r = Rect { w: 7, h: 6 };
    println!("{}", r.w * r.h);
}
