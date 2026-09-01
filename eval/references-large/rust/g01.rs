fn summarize(label: &str, readings: &[i64]) {
    let count = readings.len() as i64;
    let total: i64 = readings.iter().sum();
    let average = total / count;
    let above = readings.iter().filter(|&&r| r > average).count();
    let smallest = readings.iter().min().unwrap();
    let largest = readings.iter().max().unwrap();
    println!("{}", label);
    println!("{}", count);
    println!("{}", average);
    println!("{}", above);
    println!("{}", largest - smallest);
}

fn main() {
    let group_a = [120, 95, 143, 87, 210, 156, 99];
    let group_b = [175, 132, 88, 240, 119, 167];
    summarize("A", &group_a);
    summarize("B", &group_b);
    let total_a: i64 = group_a.iter().sum();
    let total_b: i64 = group_b.iter().sum();
    if total_a > total_b {
        println!("A");
    } else {
        println!("B");
    }
}
