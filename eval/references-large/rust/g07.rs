fn shift_word(word: &str, by: i64) -> String {
    let alphabet = "abcdefghijklmnopqrstuvwxyz";
    let mut out = String::new();
    for c in word.chars() {
        let idx = alphabet.find(c).unwrap() as i64;
        let moved = (idx + by).rem_euclid(26) as usize;
        out.push(alphabet.chars().nth(moved).unwrap());
    }
    out
}

fn main() {
    for w in ["ferry", "oxide", "cargo"] {
        let encoded = shift_word(w, 3);
        let decoded = shift_word(&encoded, -3);
        let rotated = shift_word(w, 13);
        let restored = shift_word(&rotated, 13);
        println!("{}", w);
        println!("{}", encoded);
        println!("{}", decoded);
        println!("{}", decoded == w);
        println!("{}", rotated);
        println!("{}", restored == w);
    }
}
