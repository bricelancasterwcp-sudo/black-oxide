struct Sensor { reading: i64 }
struct Device { sensor: Sensor }

fn main() {
    let mut d = Device { sensor: Sensor { reading: 0 } };
    d.sensor.reading = 7;
    println!("{}", d.sensor.reading);
}
