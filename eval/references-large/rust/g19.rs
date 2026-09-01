fn main() {
    let text = "order 47 shipped on 2026-03-15, invoice 1290 paid";
    let mut letters = 0;
    let mut digits = 0;
    let mut spaces = 0;
    let mut others = 0;
    let mut digit_run = 0;
    let mut longest_digit_run = 0;
    let mut digits_only = String::new();
    for c in text.chars() {
        if c.is_ascii_digit() {
            digits += 1;
            digit_run += 1;
            digits_only.push(c);
            if digit_run > longest_digit_run {
                longest_digit_run = digit_run;
            }
        } else {
            digit_run = 0;
            if c.is_ascii_alphabetic() {
                letters += 1;
            } else if c == ' ' {
                spaces += 1;
            } else {
                others += 1;
            }
        }
    }
    println!("{}", text.chars().count());
    println!("{}", letters);
    println!("{}", digits);
    println!("{}", spaces);
    println!("{}", others);
    println!("{}", longest_digit_run);
    println!("{}", digits_only);
}
