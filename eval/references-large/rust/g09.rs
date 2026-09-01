fn station_report(label: &str, celsius: &[i64]) -> i64 {
    let mut freezing = 0;
    let mut hot = 0;
    let mut hottest = i64::MIN;
    let mut coldest = i64::MAX;
    let mut total = 0;
    for &c in celsius {
        let f = c * 9 / 5 + 32;
        if c <= 0 {
            freezing += 1;
        }
        if c >= 30 {
            hot += 1;
        }
        if f > hottest {
            hottest = f;
        }
        if f < coldest {
            coldest = f;
        }
        total += c;
    }
    let average = total / celsius.len() as i64;
    println!("{}", label);
    println!("{}", freezing);
    println!("{}", hot);
    println!("{}", hottest);
    println!("{}", coldest);
    println!("{}", average);
    average
}

fn main() {
    let alpha = [-5, 12, 30, 22, 0, 35, 18];
    let beta = [8, -12, 5, 41, 27];
    let alpha_average = station_report("alpha", &alpha);
    let beta_average = station_report("beta", &beta);
    if alpha_average > beta_average {
        println!("alpha");
    } else {
        println!("beta");
    }
}
