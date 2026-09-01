struct Item { name: Str, quantity: Int, unit_price: Int }

fn warehouse_report(label: Str, items: Vec<Item>) -> Int {
    let total_value = 0
    let low_stock = 0
    let best_value = -1
    let best_name = ""
    for it in items {
        let value = it.quantity * it.unit_price
        total_value += value
        if it.quantity < 10 {
            low_stock += 1
        }
        if value > best_value {
            best_value = value
            best_name = it.name
        }
    }
    print_str(label)
    print(total_value)
    print(low_stock)
    print_str(best_name)
    total_value
}

fn main() {
    let north = vec().push(Item { name: "bolt", quantity: 40, unit_price: 3 }).push(Item { name: "hinge", quantity: 8, unit_price: 25 }).push(Item { name: "plate", quantity: 15, unit_price: 12 })
    let south = vec().push(Item { name: "clamp", quantity: 6, unit_price: 45 }).push(Item { name: "rod", quantity: 22, unit_price: 9 }).push(Item { name: "washer", quantity: 100, unit_price: 1 }).push(Item { name: "gasket", quantity: 4, unit_price: 30 })
    let north_total = warehouse_report("North", north)
    let south_total = warehouse_report("South", south)
    if north_total > south_total {
        print_str("North")
    } else {
        print_str("South")
    }
}
