fn trend_report(label: &str, series: &[i64]) -> i64 {
    let mut rises = 0;
    let mut falls = 0;
    let mut biggest = 0;
    let mut run = 1;
    let mut longest = 1;
    for i in 1..series.len() {
        let delta = series[i] - series[i - 1];
        if delta > 0 {
            rises += 1;
            run += 1;
            if run > longest {
                longest = run;
            }
        } else {
            if delta < 0 {
                falls += 1;
            }
            run = 1;
        }
        if delta > biggest {
            biggest = delta;
        }
    }
    println!("{}", label);
    println!("{}", rises);
    println!("{}", falls);
    println!("{}", biggest);
    println!("{}", longest);
    longest
}

fn main() {
    let north = [12, 15, 19, 14, 14, 20, 31, 30];
    let south = [40, 38, 41, 45, 50, 44];
    let north_run = trend_report("north", &north);
    let south_run = trend_report("south", &south);
    if north_run > south_run {
        println!("north");
    } else {
        println!("south");
    }
}
