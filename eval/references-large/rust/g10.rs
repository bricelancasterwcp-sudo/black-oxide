fn phrase_report(label: &str, phrase: &str) -> usize {
    let words: Vec<&str> = phrase.split(' ').collect();
    let mut longest = "";
    let mut longest_len = 0;
    let mut shortest = usize::MAX;
    let mut long_words = 0;
    for w in &words {
        let n = w.chars().count();
        if n > longest_len {
            longest_len = n;
            longest = w;
        }
        if n < shortest {
            shortest = n;
        }
        if n > 4 {
            long_words += 1;
        }
    }
    println!("{}", label);
    println!("{}", words.len());
    println!("{}", longest);
    println!("{}", shortest);
    println!("{}", long_words);
    words.len()
}

fn main() {
    let first_count = phrase_report("first", "the harbour lights flickered");
    let second_count = phrase_report("second", "a small boat drifted past silently");
    if first_count > second_count {
        println!("first");
    } else {
        println!("second");
    }
}
