struct Account {
    name: String,
    opening: i64,
    transactions: Vec<i64>,
}

fn settle(account: &Account) -> i64 {
    let mut balance = account.opening;
    let mut lowest = balance;
    let mut withdrawals = 0;
    let mut largest_deposit = 0;
    for &t in &account.transactions {
        balance += t;
        if t < 0 {
            withdrawals += 1;
        } else if t > largest_deposit {
            largest_deposit = t;
        }
        if balance < lowest {
            lowest = balance;
        }
    }
    println!("{}", account.name);
    println!("{}", balance);
    println!("{}", largest_deposit);
    println!("{}", withdrawals);
    println!("{}", lowest < 0);
    balance
}

fn main() {
    let one = Account {
        name: "ledger-one".to_string(),
        opening: 500,
        transactions: vec![200, -750, 130, -60, 400],
    };
    let two = Account {
        name: "ledger-two".to_string(),
        opening: 300,
        transactions: vec![-100, 250, -50, 75],
    };
    let first = settle(&one);
    let second = settle(&two);
    if first > second {
        println!("ledger-one");
    } else {
        println!("ledger-two");
    }
}
