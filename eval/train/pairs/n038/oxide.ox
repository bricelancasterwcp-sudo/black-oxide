struct Sensor { reading: Int }
struct Device { sensor: Sensor }

fn main() {
    let d = Device { sensor: Sensor { reading: 0 } }
    d.sensor.reading = 7
    print(d.sensor.reading)
}
