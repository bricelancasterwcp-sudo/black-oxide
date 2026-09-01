fn main() {
    let values = [4, 4, 4, 7, 7, 2, 9, 9, 9, 9, 1, 1, 5];
    let mut longest_run = 1;
    let mut longest_value = values[0];
    let mut current_run = 1;
    let mut distinct: Vec<i64> = Vec::new();
    let mut first_duplicate = -1;
    let mut sorted = true;
    for i in 0..values.len() {
        if i > 0 {
            if values[i] == values[i - 1] {
                current_run += 1;
            } else {
                current_run = 1;
            }
            if current_run > longest_run {
                longest_run = current_run;
                longest_value = values[i];
            }
            if values[i] < values[i - 1] {
                sorted = false;
            }
        }
        if distinct.contains(&values[i]) {
            if first_duplicate == -1 {
                first_duplicate = i as i64;
            }
        } else {
            distinct.push(values[i]);
        }
    }
    println!("{}", values.len());
    println!("{}", longest_run);
    println!("{}", longest_value);
    println!("{}", distinct.len());
    println!("{}", first_duplicate);
    println!("{}", sorted);
}
