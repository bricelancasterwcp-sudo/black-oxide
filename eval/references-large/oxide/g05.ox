struct Account { name: Str, opening: Int, transactions: Vec<Int> }

fn settle(account: Account) -> Int {
    let balance = account.opening
    let lowest = balance
    let withdrawals = 0
    let largest_deposit = 0
    for t in account.transactions {
        balance += t
        if t < 0 {
            withdrawals += 1
        } else if t > largest_deposit {
            largest_deposit = t
        }
        if balance < lowest {
            lowest = balance
        }
    }
    print_str(account.name)
    print(balance)
    print(largest_deposit)
    print(withdrawals)
    print(lowest < 0)
    balance
}

fn main() {
    let one = Account { name: "ledger-one", opening: 500, transactions: vec().push(200).push(-750).push(130).push(-60).push(400) }
    let two = Account { name: "ledger-two", opening: 300, transactions: vec().push(-100).push(250).push(-50).push(75) }
    let first = settle(one)
    let second = settle(two)
    if first > second {
        print_str("ledger-one")
    } else {
        print_str("ledger-two")
    }
}
