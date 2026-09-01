fn main() {
    let record = "name=widget;qty=17;price=245;tag=blue"
    let keys = vec()
    let values = vec()
    let key = ""
    let value = ""
    let in_value = false
    for c in chars(record) {
        if c == "=" {
            in_value = true
        } else if c == ";" {
            keys = push(keys, key)
            values = push(values, value)
            key = ""
            value = ""
            in_value = false
        } else if in_value {
            value = concat(value, c)
        } else {
            key = concat(key, c)
        }
    }
    keys = push(keys, key)
    values = push(values, value)
    print(len(keys))
    for i in range(0, len(keys)) {
        print_str(unwrap_or(get(keys, i), ""))
        print_str(unwrap_or(get(values, i), ""))
    }
    let qty = unwrap_or(parse_int(unwrap_or(get(values, 1), "")), 0)
    let price = unwrap_or(parse_int(unwrap_or(get(values, 2), "")), 0)
    print(qty * price)
}
