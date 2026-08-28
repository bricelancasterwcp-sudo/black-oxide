struct Rect { w: i64, h: i64 }

fn main() {
    let mut r = Rect { w: 2, h: 3 };
    r.w = 5;
    println!("{}", r.w * r.h);
}
