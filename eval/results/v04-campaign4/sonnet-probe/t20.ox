struct Item { name: Str, price: Int, qty: Int }

fn main() {
    let items = vec()
    items = push(items, Item { name: "pen", price: 3, qty: 4 })
    items = push(items, Item { name: "pad", price: 9, qty: 2 })
    items = push(items, Item { name: "ink", price: 5, qty: 3 })

    let total = 0
    for item in items {
        total += item.price * item.qty
    }
    print(total)

    let best_name = ""
    let best_cost = -1
    for item in items {
        let cost = item.price * item.qty
        if cost > best_cost {
            best_cost = cost
            best_name = item.name
        }
    }
    print_str(best_name)
}
