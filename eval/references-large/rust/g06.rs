fn band_report(label: &str, scores: &[i64]) -> i64 {
    let mut top = 0;
    let mut high = 0;
    let mut mid = 0;
    let mut pass = 0;
    let mut fail = 0;
    let mut total = 0;
    for &s in scores {
        total += s;
        if s >= 90 {
            high += 1;
        } else if s >= 80 {
            mid += 1;
        } else if s >= 70 {
            pass += 1;
        } else {
            fail += 1;
        }
        if s > top {
            top = s;
        }
    }
    let average = total / scores.len() as i64;
    println!("{}", label);
    println!("{}", high);
    println!("{}", mid);
    println!("{}", pass);
    println!("{}", fail);
    println!("{}", top);
    println!("{}", average);
    average
}

fn main() {
    let morning = [94, 71, 88, 65, 92, 79, 83];
    let evening = [55, 90, 77, 84, 68, 99];
    let morning_average = band_report("morning", &morning);
    let evening_average = band_report("evening", &evening);
    if morning_average > evening_average {
        println!("morning");
    } else {
        println!("evening");
    }
}
