fn main() {
    let left = [2, 5, 9, 14, 21, 30];
    let right = [1, 5, 8, 15, 22];
    let mut merged: Vec<i64> = Vec::new();
    let mut i = 0;
    let mut j = 0;
    while i < left.len() && j < right.len() {
        if left[i] <= right[j] {
            merged.push(left[i]);
            i += 1;
        } else {
            merged.push(right[j]);
            j += 1;
        }
    }
    while i < left.len() {
        merged.push(left[i]);
        i += 1;
    }
    while j < right.len() {
        merged.push(right[j]);
        j += 1;
    }
    let mut sorted = true;
    let mut duplicates = 0;
    for k in 1..merged.len() {
        if merged[k] < merged[k - 1] {
            sorted = false;
        }
        if merged[k] == merged[k - 1] {
            duplicates += 1;
        }
    }
    println!("{}", merged.len());
    println!("{}", merged[0]);
    println!("{}", merged[merged.len() - 1]);
    println!("{}", merged.iter().sum::<i64>());
    println!("{}", sorted);
    println!("{}", duplicates);
}
