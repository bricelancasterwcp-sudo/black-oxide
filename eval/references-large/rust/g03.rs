struct Item {
    name: String,
    quantity: i64,
    unit_price: i64,
}

fn warehouse_report(label: &str, items: &[Item]) -> i64 {
    let total_value: i64 = items.iter().map(|i| i.quantity * i.unit_price).sum();
    let low_stock = items.iter().filter(|i| i.quantity < 10).count();
    let most = items
        .iter()
        .max_by_key(|i| i.quantity * i.unit_price)
        .unwrap();
    println!("{}", label);
    println!("{}", total_value);
    println!("{}", low_stock);
    println!("{}", most.name);
    total_value
}

fn item(name: &str, quantity: i64, unit_price: i64) -> Item {
    Item {
        name: name.to_string(),
        quantity,
        unit_price,
    }
}

fn main() {
    let north = [
        item("bolt", 40, 3),
        item("hinge", 8, 25),
        item("plate", 15, 12),
    ];
    let south = [
        item("clamp", 6, 45),
        item("rod", 22, 9),
        item("washer", 100, 1),
        item("gasket", 4, 30),
    ];
    let north_total = warehouse_report("North", &north);
    let south_total = warehouse_report("South", &south);
    if north_total > south_total {
        println!("North");
    } else {
        println!("South");
    }
}
