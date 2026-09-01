struct Config { workers: Int, retries: Int, timeout: Int, label: Str }

fn show(c: Config) {
    print_str(c.label)
    print(c.workers)
    print(c.retries)
    print(c.timeout)
    print(c.workers * c.timeout)
}

fn main() {
    let base = Config { workers: 4, retries: 2, timeout: 30, label: "base" }
    show(base)
    let tuned = Config { workers: 8, label: "tuned", ..base }
    show(tuned)
    let patient = Config { timeout: 90, label: "patient", ..tuned }
    show(patient)
    let settled = Config { retries: 5, label: "settled", ..patient }
    show(settled)
    let wide = Config { workers: 16, label: "wide", ..settled }
    show(wide)
    let last = Config { timeout: 120, label: "last", ..wide }
    show(last)
    print(last.workers + last.retries + last.timeout)
}
