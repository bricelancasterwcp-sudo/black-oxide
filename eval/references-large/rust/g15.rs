fn main() {
    let record = "name=widget;qty=17;price=245;tag=blue";
    let mut keys: Vec<String> = Vec::new();
    let mut values: Vec<String> = Vec::new();
    let mut key = String::new();
    let mut value = String::new();
    let mut in_value = false;
    for c in record.chars() {
        if c == '=' {
            in_value = true;
        } else if c == ';' {
            keys.push(key.clone());
            values.push(value.clone());
            key.clear();
            value.clear();
            in_value = false;
        } else if in_value {
            value.push(c);
        } else {
            key.push(c);
        }
    }
    keys.push(key);
    values.push(value);
    println!("{}", keys.len());
    for i in 0..keys.len() {
        println!("{}", keys[i]);
        println!("{}", values[i]);
    }
    let qty: i64 = values[1].parse().unwrap();
    let price: i64 = values[2].parse().unwrap();
    println!("{}", qty * price);
}
