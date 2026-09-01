struct Config {
    workers: i64,
    retries: i64,
    timeout: i64,
    label: String,
}

fn show(c: &Config) {
    println!("{}", c.label);
    println!("{}", c.workers);
    println!("{}", c.retries);
    println!("{}", c.timeout);
    println!("{}", c.workers * c.timeout);
}

fn main() {
    let base = Config {
        workers: 4,
        retries: 2,
        timeout: 30,
        label: "base".to_string(),
    };
    show(&base);
    let tuned = Config {
        workers: 8,
        label: "tuned".to_string(),
        ..base
    };
    show(&tuned);
    let patient = Config {
        timeout: 90,
        label: "patient".to_string(),
        ..tuned
    };
    show(&patient);
    let settled = Config {
        retries: 5,
        label: "settled".to_string(),
        ..patient
    };
    show(&settled);
    let wide = Config {
        workers: 16,
        label: "wide".to_string(),
        ..settled
    };
    show(&wide);
    let last = Config {
        timeout: 120,
        label: "last".to_string(),
        ..wide
    };
    show(&last);
    println!("{}", last.workers + last.retries + last.timeout);
}
